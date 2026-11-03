# Conversa `example-04-promocoes-e-indisponivel-1793707539`

_Relógio da loja: terça-feira, 03/11/2026 10:30 (horário de Campo Grande) — loja ABERTA agora (hoje fecha às 18:00)_

**Cliente:** Tem promoção de Black Friday?

> 🔧 `search_products(on_promotion=True)`

**Clave:** Oi! Não tenho uma campanha de Black Friday ativa no sistema agora. 🎸

O que tem de promoção hoje são esses itens:

- Ukulele Kalani KAL-700T Tenor — de R$ 359,00 por R$ 323,10 (10% off)
- Ukulele Ohana CK-20 Concert — de R$ 549,00 por R$ 439,20 (20% off)
- Violão Crafter HT-100 Folk Aço — de R$ 2.399,00 por R$ 1.967,18 (18% off)
- Violão Taylor 110e Dreadnought — de R$ 5.999,00 por R$ 5.519,08 (8% off)

Quer ver mais detalhes de algum ou buscar outra coisa?

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

**Cliente:** E o violão Giannini GF-3D, vocês têm?

> 🔧 `get_product_details(name='Giannini GF-3D'); search_products(category='Violões', include_unavailable=False)`

**Clave:** O Giannini GF-3D Dreadnought Sunburst está temporariamente indisponível no momento. 😔

Mas temos outras opções de violão disponíveis, por exemplo:

- Giannini GF-1R Aço Folk Sunburst — R$ 579,90
- Yamaha F310 Aço Natural — R$ 699,90
- Tagima Dallas Tuner Aço Natural — R$ 749,00
- Shelby SGD-195E Elétrico Aço Sunburst — R$ 799,00

Quer saber mais detalhes de algum desses ou procurar outro modelo?

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

**Cliente:** Quanto fica o Crafter HT-100 no PIX?

> 🔧 `get_payment_options(product_ids=[90])`

**Clave:** O Crafter HT-100 Folk Aço está em promoção por R$ 1.967,18. No PIX fica o mesmo valor, porque o desconto de 5% do PIX não se acumula com preços promocionais.

Quer fechar ou precisa de mais alguma coisa?

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

