# Caches de shaders ao trocar de driver

O Eden pode reconstruir pipelines quando o driver muda. O cache do jogo guarda shaders e estados observados durante a execução; o cache Vulkan do driver guarda dados específicos da GPU/driver. Uma nova versão do driver pode invalidar esses dados. Não é possível gerar todos os shaders de cenas nunca executadas somente a partir do APK do emulador.

`scripts/eden-cache-profiles.py` guarda o cache Vulkan de cada driver para reutilizá-lo ao voltar à mesma biblioteca e à mesma revisão informada do Eden. O primeiro uso de um driver continua exigindo compilação. A ferramenta não é um compilador offline nem faz pré-aquecimento da GPU; ela preserva resultados anteriores.

## Escopo e compatibilidade

- Funciona em uma **pasta de cache exportada**, com Python 3.10 ou posterior, em PC ou Termux. Não acessa automaticamente a pasta privada do Eden no Android.
- Para Borderlands 2, a pasta deve se chamar `010096f00ff22000` e conter `vulkan.bin` e `vulkan_pipelines.bin`.
- Reconhece os cabeçalhos `yuzucach`, `yuzuvkch` e o cabeçalho Vulkan v1. Esses formatos foram verificados na base Eden v0.2.1; um cache real da Nightly `4dc69c06f7` ainda não foi fornecido. Um formato desconhecido é recusado.
- A identidade do driver é o SHA256 da biblioteca ARM64 dentro do ZIP, não seu nome. A revisão do Eden é informada pelo usuário. Salve usando o ZIP do driver que realmente gerou o cache; a ferramenta não pode confirmar qual driver estava carregado no telefone.
- O UUID Vulkan, fabricante/dispositivo, versão de cache e hashes são registrados. Essa inspeção não valida todos os registros internos do cache nem comprova compatibilidade em execução.
- Restaura somente `vulkan_pipelines.bin`. Preserva `vulkan.bin`, inclusive shaders descobertos depois do perfil salvo, e faz backup do cache Vulkan substituído. Dados que não existiam no perfil antigo ainda podem ser recompilados.
- Perfis são separados por jogo, revisão do Eden e biblioteca do driver. Eles precisam ser gerados no seu próprio aparelho. Não compartilhe exportações completas de dados do emulador: a ferramenta só precisa desses dois arquivos e do ZIP do driver.

## Uso

1. Jogue com o driver A para gerar o cache e feche completamente o Eden.
2. Exporte/copie a pasta de cache do jogo para um local acessível. Use o recurso de exportação/acesso aos arquivos disponível na sua instalação; esta ferramenta não contorna o armazenamento restrito do Android 16. Não envie chaves ou arquivos do jogo.
3. Inspecione e salve o perfil A:

```bash
python3 scripts/eden-cache-profiles.py inspect \
  --cache-dir cache-exportado/shader/010096f00ff22000

python3 scripts/eden-cache-profiles.py save \
  --cache-dir cache-exportado/shader/010096f00ff22000 \
  --driver Turnip_Gen8_V37.zip \
  --emulator 4dc69c06f7 --profiles meus-perfis --eden-stopped
```

4. Repita para o driver B depois de jogar com ele.
5. Quando voltar ao driver A, feche o Eden, exporte a pasta atual e restaure o perfil correspondente antes da próxima execução:

```bash
python3 scripts/eden-cache-profiles.py restore \
  --cache-dir cache-exportado/shader/010096f00ff22000 \
  --driver Turnip_Gen8_V37.zip \
  --emulator 4dc69c06f7 --profiles meus-perfis --eden-stopped
```

6. Retorne o `vulkan_pipelines.bin` preparado à pasta do jogo pelo mesmo mecanismo de importação/acesso aos arquivos da sua instalação. Se só houver exportação/importação de todos os dados, preserve a estrutura original da exportação e seus demais arquivos. Não importe uma exportação antiga inteira para fazer esta troca.

O Eden ainda precisa ler os shaders e reconstruir seus objetos Vulkan no início. Restaurar um cache compatível pode acelerar essa etapa; não elimina o carregamento e não garante zero travamentos. Se o emulador rejeitar o cache, ele poderá recompilar normalmente. O resultado no aparelho deve ser verificado em duas execuções com o mesmo driver.

## Validação

```bash
python3 -m unittest discover -s tests -p 'test_eden_cache_profiles.py' -v
```

Os testes cobrem restauração com backup, preservação de novos shaders, isolamento por driver/revisão, corrupção, mudança de formato, arquivos vazios, links simbólicos e uso dos ZIPs reais deste repositório. Os payloads de cache dos testes são sintéticos; não constituem validação de um cache real da Nightly ou da execução de Borderlands 2.
