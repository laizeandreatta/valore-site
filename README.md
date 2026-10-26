# Site da Valore Imobiliária

Site público em https://valoreimobiliaria.com, gerado a partir do painel interno.

- `tools/build.py <export-do-painel>` gera a pasta `docs/` (publicada pelo GitHub Pages).
- Só vão para o site os imóveis marcados "Mostrar no site = Sim" no painel, e só os campos públicos
  (título e texto do site, região, rua sem número, área, quartos, suítes, vagas, valor, diferenciais, fotos e vídeo).
- Proprietário, contatos, comissão, parceria e observações internas nunca entram neste repositório.
- Fotos: `src/fotos/<id-do-imóvel>/01.jpg, 02.jpg…` e `video.mp4`. A 01 é a capa.
- Contatos do site (WhatsApp, e-mail, Instagram, CRECI): `site.json`.
