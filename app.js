function buscarEndereco(tipo) {
  const cep = document.getElementById('cep' + tipo).value.replace(/\D/g, '');
  if (cep.length !== 8) return alert("CEP inválido");
  fetch(`https://viacep.com.br/ws/${cep}/json/`)
    .then(res => res.json())
    .then(data => {
      if (data.erro) return alert("CEP não encontrado");
      document.getElementById('rua' + tipo).value = data.logradouro;
      document.getElementById('bairro' + tipo).value = data.bairro;
      document.getElementById('cidade' + tipo).value = data.localidade;
    });
}

function enviarParaWhatsApp() {
  const nome = document.getElementById('nomeSolicitante').value;
  const tel = document.getElementById('telefoneSolicitante').value;
  const acao = document.querySelector('input[name="acao"]:checked').value;

  let servicos = Array.from(document.querySelectorAll('input[type=checkbox]:checked'))
    .filter(el => el.id !== 'temRetorno')
    .map(cb => cb.value || document.getElementById('outrosDescricao').value);

  let pagamentos = Array.from(document.querySelectorAll('input[type=checkbox]:checked'))
    .filter(el => ['Pix','Dinheiro','Contrato'].includes(el.value))
    .map(cb => cb.value);

  const retorno = document.getElementById('temRetorno').checked ? "Sim" : "Não";
  const nomeRecebedor = document.getElementById('nomeRecebedor').value;
  const telRecebedor = document.getElementById('telefoneRecebedor').value;

  const coleta = `${document.getElementById('ruaColeta').value}, ${document.getElementById('numeroColeta').value}, ${document.getElementById('bairroColeta').value}, ${document.getElementById('cidadeColeta').value}`;
  const entrega = `${document.getElementById('ruaEntrega').value}, ${document.getElementById('numeroEntrega').value}, ${document.getElementById('bairroEntrega').value}, ${document.getElementById('cidadeEntrega').value}`;

  let msg = `📦 *COOPEX ENTREGAS - ${acao}*\n`;
  msg += `👤 *Solicitante:* ${nome}\n📞 *Telefone:* ${tel}\n`;
  msg += `🏠 *Coleta:* ${coleta}\n`;
  msg += `📍 *Entrega:* ${entrega}\n`;
  if (nomeRecebedor) msg += `🎯 *Recebedor:* ${nomeRecebedor}\n`;
  if (telRecebedor) msg += `📱 *Tel Recebedor:* ${telRecebedor}\n`;
  msg += `🛠️ *Serviço:* ${servicos.join(", ")}\n`;
  msg += `💰 *Pagamento:* ${pagamentos.join(", ")}\n`;
  msg += `🔁 *Retorno:* ${retorno}`;

  const url = `https://wa.me/5584981110706?text=${encodeURIComponent(msg)}`;
  window.open(url, '_blank');
}