/* Lógica da página Monte sua Pizza */
document.addEventListener('DOMContentLoaded', () => {
  let selectedMassaExtra = 0;
  let selectedBordaExtra = 0;
  let selectedSabores    = [];  // [{id, preco, nome}]

  const precoEl   = document.getElementById('preco-preview');
  const prevEl    = document.getElementById('sabores-preview');
  const btnAdd    = document.getElementById('btn-add');
  const form      = document.getElementById('form-pizza');
  const fMassa    = document.getElementById('f-massa');
  const fBorda    = document.getElementById('f-borda');

  // ── Massa / Borda ──────────────────────────────────────────
  document.querySelectorAll('.opt-card').forEach(card => {
    card.addEventListener('click', () => {
      const type = card.dataset.type;
      document.querySelectorAll(`.opt-card[data-type="${type}"]`).forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      const extra = parseFloat(card.dataset.extra) || 0;
      if (type === 'massa') { selectedMassaExtra = extra; fMassa.value = card.dataset.id; }
      else                  { selectedBordaExtra = extra; fBorda.value = card.dataset.id; }
      updatePrice();
    });
  });

  // ── Sabores ────────────────────────────────────────────────
  document.querySelectorAll('.sabor-card').forEach(card => {
    card.addEventListener('click', () => {
      const id    = +card.dataset.id;
      const preco = parseFloat(card.dataset.preco);
      const nome  = card.dataset.nome;
      const idx   = selectedSabores.findIndex(s => s.id === id);

      if (idx >= 0) {
        selectedSabores.splice(idx, 1);
        card.classList.remove('selected');
      } else if (selectedSabores.length < 3) {
        selectedSabores.push({id, preco, nome});
        card.classList.add('selected');
      }

      // Desabilita não-selecionados quando já tem 3
      document.querySelectorAll('.sabor-card').forEach(c => {
        const cid = +c.dataset.id;
        const sel = selectedSabores.some(s => s.id === cid);
        c.classList.toggle('disabled', selectedSabores.length >= 3 && !sel);
      });

      updatePrice();
      syncInputs();
    });
  });

  // ── Filtro de categoria ───────────────────────────────────
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active', 'btn-orange'));
      btn.classList.add('active', 'btn-orange');
      const cat = btn.dataset.cat;
      document.querySelectorAll('.sabor-item').forEach(item => {
        item.style.display = (cat === 'all' || item.dataset.cat === cat) ? '' : 'none';
      });
    });
  });

  // ── Helpers ───────────────────────────────────────────────
  function updatePrice() {
    if (!selectedSabores.length) {
      precoEl.textContent = 'R$ --';
      prevEl.textContent  = 'Selecione ao menos 1 sabor';
      btnAdd.disabled = true;
      return;
    }
    const avg  = selectedSabores.reduce((s, x) => s + x.preco, 0) / selectedSabores.length;
    const total = avg + selectedMassaExtra + selectedBordaExtra;
    precoEl.textContent = 'R$ ' + total.toFixed(2).replace('.', ',');
    prevEl.textContent  = selectedSabores.map(s => s.nome).join(' + ');
    btnAdd.disabled = false;
  }

  function syncInputs() {
    // Remove inputs anteriores
    form.querySelectorAll('input[name="sabor_ids"]').forEach(i => i.remove());
    selectedSabores.forEach(s => {
      const inp = document.createElement('input');
      inp.type  = 'hidden';
      inp.name  = 'sabor_ids';
      inp.value = s.id;
      form.appendChild(inp);
    });
  }

  // Init: seleciona primeira massa e borda
  const firstMassa = document.querySelector('.opt-card[data-type="massa"].selected');
  const firstBorda = document.querySelector('.opt-card[data-type="borda"].selected');
  if (firstMassa) selectedMassaExtra = parseFloat(firstMassa.dataset.extra) || 0;
  if (firstBorda) selectedBordaExtra = parseFloat(firstBorda.dataset.extra) || 0;
});
