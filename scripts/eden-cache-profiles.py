#!/usr/bin/env python3
"""Store driver-specific Eden pipeline caches from an exported cache directory."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import uuid
import zipfile

RAW = "vulkan.bin"
PIPELINES = "vulkan_pipelines.bin"
MAX_CACHE = 1024 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file(path: Path, limit: int = MAX_CACHE) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Arquivo normal obrigatório: {path}")
    before = path.stat()
    if before.st_size > limit:
        raise ValueError(f"Arquivo excede o limite de {limit} bytes: {path}")
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"Arquivo mudou durante a leitura: {path}")
    return data


def parse_raw(data: bytes) -> dict:
    if len(data) <= 12 or data[:8] != b"yuzucach":
        raise ValueError("vulkan.bin ausente, vazio ou com cabeçalho não reconhecido")
    return {"cache_version": struct.unpack_from("<I", data, 8)[0],
            "size": len(data), "sha256": digest(data)}


def parse_pipelines(data: bytes) -> dict:
    if len(data) < 44 or data[:8] != b"yuzuvkch":
        raise ValueError("Cache Vulkan do driver tem cabeçalho Eden não reconhecido")
    cache_version = struct.unpack_from("<I", data, 8)[0]
    blob = data[12:]
    size, version, vendor, device = struct.unpack_from("<IIII", blob)
    if version != 1 or not 32 <= size <= len(blob):
        raise ValueError("Cabeçalho Vulkan v1 inválido ou versão não suportada")
    if len(blob) <= size:
        raise ValueError("Cache do driver vazio: ainda não há payload para preservar")
    return {"cache_version": cache_version, "header_version": version,
            "vendor_id": f"0x{vendor:08x}", "device_id": f"0x{device:08x}",
            "pipeline_cache_uuid": blob[16:32].hex(),
            "size": len(data), "sha256": digest(data)}


def driver_identity(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("ZIP do driver contém entradas duplicadas")
        meta_entry = archive.getinfo("meta.json")
        if meta_entry.file_size > 16384:
            raise ValueError("meta.json grande demais")
        meta = json.loads(archive.read(meta_entry))
        if not isinstance(meta, dict):
            raise ValueError("meta.json deve conter um objeto")
        library = meta["libraryName"]
        if not isinstance(library, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.so", library):
            raise ValueError("libraryName deve ser um nome simples de biblioteca .so")
        if archive.getinfo(library).file_size > 64 * 1024 * 1024:
            raise ValueError("Biblioteca do driver excede 64 MiB")
        binary = archive.read(library)
        if len(binary) < 20 or binary[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", binary, 18)[0] != 183:
            raise ValueError("Este gerenciador exige um driver ELF ARM64 little-endian")
    return {"name": str(meta.get("name", library)), "library": library,
            "library_sha256": digest(binary)}


def check_args(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"[0-9a-fA-F]{16}", args.title):
        raise ValueError("Title ID deve conter 16 dígitos hexadecimais")
    args.title = args.title.lower()
    if args.cache_dir.name.lower() != args.title:
        raise ValueError(f"Selecione a pasta do jogo chamada {args.title}")
    if not args.cache_dir.is_dir() or args.cache_dir.is_symlink():
        raise ValueError("Pasta de cache deve existir e não pode ser um link simbólico")


def save(args: argparse.Namespace) -> dict:
    check_args(args)
    driver = driver_identity(args.driver)
    raw = parse_raw(read_file(args.cache_dir / RAW))
    pipeline_data = read_file(args.cache_dir / PIPELINES)
    pipelines = parse_pipelines(pipeline_data)
    if raw["cache_version"] != pipelines["cache_version"]:
        raise ValueError("Caches do jogo e do driver têm versões diferentes")
    profile_root = args.profiles / args.title / digest(args.emulator.encode()) / driver["library_sha256"]
    profile_root.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    target = profile_root / name
    staging = Path(tempfile.mkdtemp(prefix=".saving-", dir=profile_root))
    try:
        (staging / PIPELINES).write_bytes(pipeline_data)
        metadata = {"schema": 1, "title_id": args.title, "emulator": args.emulator,
                    "driver": driver, "pipelines": pipelines, "raw_cache_at_save": raw,
                    "association": "driver selected by user; not verified on device"}
        (staging / "profile.json").write_text(json.dumps(metadata, indent=2) + "\n")
        os.replace(staging, target)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return {"status": "saved", "profile": str(target), "driver": driver["name"],
            "pipeline_cache_uuid": pipelines["pipeline_cache_uuid"],
            "compilation_performed": False}


def restore(args: argparse.Namespace) -> dict:
    check_args(args)
    driver = driver_identity(args.driver)
    raw = parse_raw(read_file(args.cache_dir / RAW))
    profile_root = args.profiles / args.title / digest(args.emulator.encode()) / driver["library_sha256"]
    choices = sorted(p for p in profile_root.glob("*/profile.json") if not p.parent.name.startswith("."))
    if not choices:
        raise ValueError("Nenhum perfil para esta biblioteca e versão informada do Eden; compile normalmente e salve depois")
    profile = choices[-1].parent
    metadata = json.loads(read_file(profile / "profile.json", 65536))
    if not isinstance(metadata, dict):
        raise ValueError("Metadados do perfil devem conter um objeto")
    if metadata.get("schema") != 1 or metadata.get("title_id") != args.title or metadata.get("emulator") != args.emulator or metadata.get("driver", {}).get("library_sha256") != driver["library_sha256"]:
        raise ValueError("Identidade do perfil não corresponde ao jogo, Eden e biblioteca selecionados")
    data = read_file(profile / PIPELINES)
    pipelines = parse_pipelines(data)
    if pipelines != metadata["pipelines"]:
        raise ValueError("Conteúdo do perfil foi alterado ou corrompido")
    if pipelines["cache_version"] != raw["cache_version"]:
        raise ValueError("Perfil tem versão de cache diferente da pasta atual do jogo")
    destination = args.cache_dir / PIPELINES
    backup = None
    if destination.exists() or destination.is_symlink():
        old = read_file(destination)
        backup_root = args.profiles / "restore-backups" / args.title
        backup_root.mkdir(parents=True, exist_ok=True)
        backup = backup_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex + ".bin")
        with backup.open("xb") as handle:
            handle.write(old)
        if read_file(backup) != old:
            raise ValueError("Não foi possível confirmar o backup do cache atual")
    fd, temp_name = tempfile.mkstemp(prefix=".pipeline-restore-", dir=args.cache_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        current_raw = parse_raw(read_file(args.cache_dir / RAW))
        if current_raw != raw:
            raise ValueError("Cache de shaders mudou durante a restauração")
        os.replace(temp_name, destination)
    finally:
        Path(temp_name).unlink(missing_ok=True)
    return {"status": "restored", "profile": str(profile), "destination": str(destination),
            "backup": str(backup) if backup else None, "raw_shader_cache": "unchanged",
            "compilation_performed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preserva caches Vulkan de drivers já usados; não compila shaders novos.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "save", "restore"):
        sub = commands.add_parser(command)
        sub.add_argument("--cache-dir", type=Path, required=True, help="Pasta exportada shader/<TitleID>")
        sub.add_argument("--title", default="010096f00ff22000")
        if command != "inspect":
            sub.add_argument("--driver", type=Path, required=True, help="ZIP do driver que gerou/receberá este cache")
            sub.add_argument("--emulator", required=True, help="Revisão exata do Eden, por exemplo 4dc69c06f7")
            sub.add_argument("--profiles", type=Path, required=True, help="Pasta local para guardar perfis")
            sub.add_argument("--eden-stopped", action="store_true", required=True, help="Confirma que o Eden está fechado e a exportação está completa")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            check_args(args)
            result = {"raw": parse_raw(read_file(args.cache_dir / RAW)),
                      "pipelines": parse_pipelines(read_file(args.cache_dir / PIPELINES)),
                      "validation": "recognized headers; not a full shader-record validation"}
        elif args.command == "save":
            result = save(args)
        else:
            result = restore(args)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
