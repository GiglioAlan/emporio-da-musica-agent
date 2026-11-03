# Conversa `example-02-pedido-atrasado-e-reclamacao-1793707518`

_Relógio da loja: terça-feira, 03/11/2026 10:30 (horário de Campo Grande) — loja ABERTA agora (hoje fecha às 18:00)_

**Cliente:** Oi, meu pedido ainda não chegou e já faz tempo!

**Clave:** Oi! Vou ajudar a rastrear seu pedido. 🎸

Para consultar o status, preciso do número do pedido e do e-mail ou telefone cadastrado na compra. Pode me passar essas informações?

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

**Cliente:** É o pedido 8

**Clave:** Preciso também do e-mail ou telefone cadastrado na compra para consultar o pedido 8. Pode me passar um dos dois?

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

**Cliente:** anacarol.ferreira@coldmail.com

> 🔧 `get_order_status(order_id=8, customer_contact='anacarol.ferreira@coldmail.com')`

**Clave:** Oi, Ana! Desculpe a demora na resposta. Consultei o pedido 8 e ele consta como **enviado**, com código de rastreamento **BRJL5544332BR**. A previsão de entrega era 28/02/2026, então ele está bem atrasado mesmo. Peço desculpas por isso.

Você pode acompanhar o rastreamento pelo site dos Correios ou da Jadlog com esse código.

Gostaria que eu abrisse uma reclamação para a nossa equipe verificar o que aconteceu com a entrega? Eles respondem em até 24 horas úteis. Se sim, preciso do seu telefone para o protocolo.

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

**Cliente:** Sim, por favor, registra a reclamação

> 🔧 `create_support_ticket(kind='complaint', summary='Pedido 8 (Kala KA-C Concert Mogno) enviado em 15/02/2026 com previsão de entrega 28/02/2026, mas ainda não foi recebido. Atraso de 248 dias. Código de rastreamento: BRJL5544332BR.', customer_contact='anacarol.ferreira@coldmail.com', order_id=8)`

**Clave:** Registrei a reclamação para você! 📋

**Protocolo: EM-20261103-DA39**

A nossa equipe vai entrar em contato pelo e-mail **anacarol.ferreira@coldmail.com** em até 24 horas úteis para verificar o que aconteceu com a entrega do seu pedido 8.

Precisa de mais alguma coisa?

<sub>modelo: nvidia/nemotron-3.5-super-vl:free</sub>

