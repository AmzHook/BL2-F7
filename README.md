# BL2-F7 — GitHub build repository

This repository scaffold builds **BL2-F7** from the exact Eden **v0.2.1** base commit:

`58c1e20ee58efa3900ba616207d460886214480b`

Target: POCO F7 / Snapdragon 8s Gen 4 / Adreno 825, using Borderlands 2 Program ID `010096F00FF22000`.

This repository contains only the BL2-F7 patch/build tooling. It does **not** contain Borderlands 2, firmware, keys, copyrighted game assets, or a prebuilt Eden source tree.

## Driver experimental para POCO F7

Build experimental do Mesa Turnip para Adreno 825, Android 16 / HyperOS 3, com Borderlands 2 no Eden como alvo de teste:

- [Baixar driver com logs — recomendado para o primeiro teste](https://github.com/AmzHook/BL2-F7/raw/refs/heads/main/drivers/poco-f7/experimental-1/Turnip_POCO_F7_Experimental_1_Diag.zip)
- [Baixar driver sem logs — para comparação](https://github.com/AmzHook/BL2-F7/raw/refs/heads/main/drivers/poco-f7/experimental-1/Turnip_POCO_F7_Experimental_1.zip)
- [Instruções de instalação e captura de logs](drivers/poco-f7/experimental-1/LEIA-ME.txt)
- [Receita de compilação, patch e testes](drivers/poco-f7/experimental-1/Receita_POCO_F7.zip)

Importe o ZIP **sem extrair** no gerenciador de drivers GPU do Eden e selecione-o. O pacote com logs identifica a versão/GPU e registra chamadas de criação de pipelines acima de 5 ms e erros Vulkan no Android logcat, com a tag `PocoF7-Turnip`.

A compilação e as verificações do pacote passaram. Carregamento no Eden Nightly `4dc69c06f7`, execução de Borderlands 2, FPS e estabilidade ainda precisam ser validados no aparelho. Esta build não reproduz exatamente o StevenMXZ V37 nem promete melhoria de desempenho. [Origem e validação](drivers/poco-f7/experimental-1/build-manifest-diagnostic.json) · [SHA256](drivers/poco-f7/experimental-1/SHA256SUMS).

## Cache ao alternar drivers

[Gerenciador de perfis de cache](docs/SHADER-CACHE-PROFILES.md): guarda o cache Vulkan de cada driver para reutilizá-lo ao voltar à mesma biblioteca e revisão do Eden. Trabalha numa pasta exportada, preserva os shaders mais recentes e faz backup antes de restaurar. A primeira execução com um driver novo ainda precisa compilar; a ferramenta não gera shaders inéditos nem compila pipelines fora do aparelho. [Baixar script Python](https://github.com/AmzHook/BL2-F7/raw/refs/heads/main/scripts/eden-cache-profiles.py).

## Fastest way: GitHub Actions

1. Create an empty GitHub repository, for example `BL2-F7`.
2. Upload **all files and folders from this package**, including the hidden `.github` folder.
3. Commit them to the default branch.
4. Open the repository's **Actions** tab.
5. Select **Build BL2-F7 Android**.
6. Press **Run workflow**.
7. Choose:
   - `instrumented` — recommended first build. Keeps the BL2-F7 diagnostic logging used to find pipeline/DMA stalls.
   - `release` — cleaner performance build after the instrumented build is validated on the phone.
8. When the workflow finishes, open that workflow run and download the artifact named `BL2-F7-...`.

The APK is compiled in GitHub's Linux runner. You do not need Android Studio installed on your PC for this path.

## What the workflow does

The workflow automatically:

- installs Java 17;
- configures the Android SDK;
- installs Android API 36, NDK `28.2.13676358`, and CMake `3.22.1`;
- clones Eden from the upstream server, with the GitHub mirror as fallback;
- checks out the exact v0.2.1 commit;
- initializes all submodules;
- applies `patch-kit/scripts/apply_bl2_f7.py`;
- runs the BL2-F7 static verifier;
- builds the selected Android variant;
- uploads the generated APK as a GitHub Actions artifact.

## First build to use

Use **instrumented** first. On the POCO F7, run Borderlands 2 through the same test route you already use and capture logs containing:

```text
[BL2-F7]
```

The important messages include:

```text
[BL2-F7] runtime graphics pipeline build: ... us
[BL2-F7] runtime compute pipeline build: ... us
[BL2-F7] DMA sync fence wait: ... us
```

These logs tell us whether a drop is mainly caused by runtime Vulkan pipeline creation or the mandatory Sync Memory Operations fence path.

## Repository layout

```text
BL2-F7/
├── .github/
│   └── workflows/
│       └── build-bl2-f7.yml
├── patch-kit/
│   ├── files/
│   ├── scripts/
│   └── docs/
├── scripts/
│   ├── prepare-eden.sh
│   └── build-local-linux.sh
├── docs/
├── LICENSE
├── .gitignore
└── README.md
```

## Local Linux build

If you later want to build locally, install the Android SDK/NDK requirements described by Eden, then run:

```bash
./scripts/build-local-linux.sh instrumented
```

or:

```bash
./scripts/build-local-linux.sh release
```

## Licensing

The BL2-F7 modifications are intended to remain compatible with Eden's GPL licensing requirements. Eden itself remains a separate upstream project; this repository is a patch/build scaffold derived from and intended for use with its GPL source.
