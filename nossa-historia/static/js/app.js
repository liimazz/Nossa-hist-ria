(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const csrf = $('meta[name=csrf]')?.content || '';
  const HEART = 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z';
  const BUBBLE = 'M21 12a8 8 0 0 1-11.8 7L3 21l2-5.5A8 8 0 1 1 21 12z';

  // helper para criar elementos (sempre textContent => seguro contra XSS)
  function h(tag, props = {}, ...kids) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v);
    }
    kids.flat().forEach(c => c != null && e.append(c));
    return e;
  }
  function svg(path, cls) {
    const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', '0 0 24 24');
    if (cls) s.setAttribute('class', cls);
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', path);
    s.append(p);
    return s;
  }

  /* ---------- corações flutuando ---------- */
  const hearts = $('#hearts');
  if (hearts && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const n = innerWidth < 700 ? 14 : 24;
    for (let i = 0; i < n; i++) {
      const el = h('span', { class: 'fh', text: '♥' });
      el.style.left = Math.random() * 100 + '%';
      el.style.fontSize = 10 + Math.random() * 22 + 'px';
      el.style.animationDuration = 9 + Math.random() * 12 + 's';
      el.style.animationDelay = -Math.random() * 20 + 's';
      hearts.append(el);
    }
  }

  /* ---------- contador em tempo real ---------- */
  const counter = $('#counter');
  if (counter) {
    const start = new Date(counter.dataset.start).getTime();
    const dEl = $('#cDays'), hEl = $('#cH'), mEl = $('#cM'), sEl = $('#cS');
    const p2 = n => String(n).padStart(2, '0');
    const tick = () => {
      let diff = Math.max(0, Date.now() - start);
      const days = Math.floor(diff / 864e5); diff -= days * 864e5;
      const hh = Math.floor(diff / 36e5); diff -= hh * 36e5;
      const mm = Math.floor(diff / 6e4); diff -= mm * 6e4;
      const ss = Math.floor(diff / 1e3);
      dEl.textContent = days.toLocaleString('pt-BR');
      hEl.textContent = p2(hh); mEl.textContent = p2(mm); sEl.textContent = p2(ss);
    };
    tick(); setInterval(tick, 1000);
  }

  /* ---------- topo transparente -> sólido ---------- */
  const topbar = $('#topbar');
  if (topbar) {
    const onScroll = () => topbar.classList.toggle('solid', scrollY > 60);
    onScroll(); addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- barra inferior: item ativo ---------- */
  const navs = $$('.tabbar [data-nav]');
  if (navs.length && 'IntersectionObserver' in window) {
    const secs = ['inicio', 'momentos'].map(id => document.getElementById(id)).filter(Boolean);
    const io = new IntersectionObserver(es => {
      es.forEach(e => {
        if (e.isIntersecting) navs.forEach(a => a.classList.toggle('active', a.dataset.nav === e.target.id));
      });
    }, { threshold: 0.35 });
    secs.forEach(s => io.observe(s));
  }

  /* ---------- aparecer ao rolar ---------- */
  const reveals = $$('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
    }), { threshold: 0.08 });
    reveals.forEach(r => io.observe(r));
  } else reveals.forEach(r => r.classList.add('in'));

  /* ---------- filtros ---------- */
  $$('.chip').forEach(c => c.addEventListener('click', () => {
    $$('.chip').forEach(x => x.classList.toggle('active', x === c));
    const f = c.dataset.filter;
    let shown = 0;
    $$('.card').forEach(card => {
      const ok = f === 'all' || card.dataset.kind === f;
      card.classList.toggle('hidden', !ok);
      if (ok) { shown++; card.classList.add('in'); }
    });
    $('#emptyFilter')?.classList.toggle('hidden', shown > 0);
  }));

  /* ---------- curtir ---------- */
  function applyLike(id, liked, count, animate) {
    $$(`[data-like="${id}"]`).forEach(b => {
      b.classList.toggle('on', liked);
      $('.n', b).textContent = count;
      if (animate) { b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop'); }
    });
  }
  async function toggleLike(id) {
    try {
      const r = await fetch(`/api/post/${id}/like`, { method: 'POST' });
      const d = await r.json();
      applyLike(id, d.liked, d.count, d.liked);
      return d;
    } catch (e) { return null; }
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-like]');
    if (b) { e.stopPropagation(); toggleLike(b.dataset.like); }
  });

  /* ---------- tempo relativo ---------- */
  function ago(iso) {
    const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 60) return 'agora mesmo';
    if (s < 3600) return `há ${Math.floor(s / 60)} min`;
    if (s < 86400) return `há ${Math.floor(s / 3600)} h`;
    if (s < 86400 * 30) return `há ${Math.floor(s / 86400)} d`;
    return new Date(iso).toLocaleDateString('pt-BR');
  }

  /* ---------- visualizador ---------- */
  const modal = $('#modal'), sheet = $('#sheet');
  let current = null;

  function closeModal() {
    if (!modal || modal.classList.contains('hidden')) return;
    modal.classList.add('hidden');
    document.body.style.overflow = '';
    sheet.innerHTML = '';
    current = null;
  }
  modal?.addEventListener('click', e => { if (e.target.hasAttribute('data-close')) closeModal(); });
  addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  function commentNode(c, canDelete, p) {
    const node = h('div', { class: 'cm', 'data-cid': c.id },
      h('div', { class: 'avatar', text: (c.name[0] || '?').toUpperCase() }),
      h('p', {}, h('b', { text: c.name }), document.createTextNode(c.text), h('small', { text: ago(c.at) })));
    if (canDelete) {
      node.append(h('button', {
        class: 'x', text: 'apagar', onclick: async () => {
          if (!confirm('Apagar este comentário?')) return;
          const r = await fetch(`/api/comment/${c.id}/apagar`, { method: 'POST', headers: { 'X-CSRF': csrf } });
          if (r.ok) {
            const d = await r.json();
            node.remove(); setCount(p.id, d.count);
            if (!$('.cm', sheet)) $('.m-comments', sheet).append(h('p', { class: 'none', text: 'Seja o primeiro a comentar 💕' }));
          }
        }
      }));
    }
    return node;
  }
  function setCount(id, n) {
    $$(`[data-cc="${id}"]`).forEach(el => el.textContent = n);
    const t = $('#mCount', sheet); if (t) t.textContent = n;
  }

  async function openPost(id) {
    let p;
    try { p = await (await fetch(`/api/post/${id}`)).json(); } catch { return; }
    current = p;
    sheet.innerHTML = '';
    sheet.className = 'sheet ' + (p.kind === 'letter' ? 'letter-sheet' : 'has-media');

    const heartBtn = h('button', { class: 'act like' + (p.liked ? ' on' : ''), 'data-like': p.id, 'aria-label': 'Curtir' },
      svg(HEART, 'hrt'), h('b', { class: 'n', text: p.likes }));
    const actions = h('div', { class: 'm-actions' }, heartBtn,
      h('span', { class: 'act' }, svg(BUBBLE), h('b', { id: 'mCount', text: p.comments.length })));
    if (p.can_delete) {
      actions.append(h('button', {
        class: 'del', text: 'Apagar post', onclick: async () => {
          if (!confirm('Apagar este post para sempre?')) return;
          const r = await fetch(`/post/${p.id}/apagar`, { method: 'POST', headers: { 'X-CSRF': csrf } });
          if (r.ok) location.reload();
        }
      }));
    }

    const list = h('div', { class: 'm-comments' }, h('h4', { text: 'Comentários' }));
    if (!p.comments.length) list.append(h('p', { class: 'none', text: 'Seja o primeiro a comentar 💕' }));
    p.comments.forEach(c => list.append(commentNode(c, p.can_delete, p)));

    const side = h('div', { class: 'm-side' },
      h('div', { class: 'm-author' },
        h('div', { class: 'avatar', text: p.author[0] }),
        h('div', {}, h('b', { text: p.author }), h('small', { text: p.date }))),
      p.title ? h('h3', { class: 'm-title', text: p.title }) : null,
      p.body ? h('p', { class: 'm-body' + (p.kind === 'letter' ? ' letter' : ''), text: p.body }) : null,
      actions, list);

    let media = null;
    if (p.kind !== 'letter') {
      const big = svg(HEART, 'bigheart');
      let el;
      if (p.kind === 'photo') {
        el = h('img', { src: p.url, alt: p.title || 'Foto', draggable: 'false' });
        let last = 0;
        const dbl = async () => {
          big.classList.remove('show'); void big.getBoundingClientRect(); big.classList.add('show');
          if (!$('.like', sheet).classList.contains('on')) toggleLike(p.id);
        };
        media = h('div', { class: 'm-media' }, el, big);
        media.addEventListener('dblclick', dbl);
        media.addEventListener('touchend', e => {
          const now = Date.now();
          if (now - last < 300) { e.preventDefault(); dbl(); }
          last = now;
        });
      } else {
        el = h('video', { src: p.url, controls: '', playsinline: '', preload: 'metadata' });
        media = h('div', { class: 'm-media' }, el, big);
      }
    }

    const nameIn = h('input', { class: 'nm', placeholder: 'Seu nome', maxlength: '40', autocomplete: 'nickname' });
    const textIn = h('input', { placeholder: 'Escreva um comentário…', maxlength: '400' });
    nameIn.value = localStorage.getItem('nh_nome') || '';
    const err = h('div', { class: 'err hidden' });
    const form = h('form', { class: 'm-form' },
      h('div', { class: 'r1' }, nameIn, textIn, h('button', { text: 'Enviar' })), err);
    form.addEventListener('submit', async e => {
      e.preventDefault();
      err.classList.add('hidden');
      const name = nameIn.value.trim(), text = textIn.value.trim();
      if (!name || !text) { err.textContent = 'Preencha seu nome e o comentário.'; err.classList.remove('hidden'); return; }
      const r = await fetch(`/api/post/${p.id}/comment`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, text })
      });
      const d = await r.json();
      if (!r.ok) { err.textContent = d.erro || 'Algo deu errado.'; err.classList.remove('hidden'); return; }
      localStorage.setItem('nh_nome', name);
      $('.none', list)?.remove();
      list.append(commentNode(d.comment, p.can_delete, p));
      setCount(p.id, d.count);
      textIn.value = '';
      list.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });

    const scroller = h('div', { class: 'm-scroll' }, media, side);
    sheet.append(h('button', { class: 'm-close', 'aria-label': 'Fechar', text: '×', onclick: closeModal }), scroller, form);
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  $$('.card').forEach(card => {
    const open = () => openPost(card.dataset.id);
    card.addEventListener('click', e => { if (!e.target.closest('[data-like]')) open(); });
    card.addEventListener('keydown', e => { if (e.key === 'Enter') open(); });
  });

  /* ---------- página "novo momento" ---------- */
  const form = $('#novoForm');
  if (form) {
    const radios = $$('input[name=modo]', form);
    const boxMidia = $('#boxMidia'), lbl = $('#lblTexto'), texto = $('#texto');
    const arquivo = $('#arquivo'), prev = $('#prev'), prevV = $('#prevV'), dropTxt = $('#dropTxt');
    const erro = $('#erro'), prog = $('#prog'), bar = $('#progBar'), btn = $('#enviar');

    const mode = () => radios.find(r => r.checked).value;
    const sync = () => {
      const letter = mode() === 'cartinha';
      boxMidia.classList.toggle('hidden', letter);
      lbl.innerHTML = letter ? 'Sua cartinha' : 'Legenda <small>(opcional)</small>';
      texto.rows = letter ? 9 : 4;
      texto.placeholder = letter ? 'Escreva do fundo do coração… 💌' : 'Escreva algo sobre esse momento...';
      texto.required = letter;
    };
    radios.forEach(r => r.addEventListener('change', sync)); sync();

    arquivo.addEventListener('change', () => {
      const f = arquivo.files[0];
      prev.classList.add('hidden'); prevV.classList.add('hidden');
      if (!f) { dropTxt.classList.remove('hidden'); return; }
      const url = URL.createObjectURL(f);
      if (f.type.startsWith('video')) { prevV.src = url; prevV.classList.remove('hidden'); }
      else { prev.src = url; prev.classList.remove('hidden'); }
      dropTxt.classList.add('hidden');
    });

    form.addEventListener('submit', e => {
      e.preventDefault();
      erro.classList.add('hidden');
      if (mode() === 'midia') {
        const f = arquivo.files[0];
        if (!f) { erro.textContent = 'Escolha uma foto ou um vídeo.'; erro.classList.remove('hidden'); return; }
        if (f.size > 80 * 1024 * 1024) { erro.textContent = 'Arquivo grande demais (máx. 80 MB).'; erro.classList.remove('hidden'); return; }
      }
      const fd = new FormData(form);
      if (mode() === 'cartinha') fd.delete('arquivo');
      const xhr = new XMLHttpRequest();
      xhr.open('POST', form.action || location.href);
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.upload.onprogress = ev => {
        if (ev.lengthComputable) bar.style.width = (ev.loaded / ev.total * 100) + '%';
      };
      xhr.onloadstart = () => { prog.classList.remove('hidden'); btn.disabled = true; btn.textContent = 'Enviando…'; };
      xhr.onload = () => {
        let d = {};
        try { d = JSON.parse(xhr.responseText); } catch { }
        if (xhr.status === 200 && d.ok) { btn.textContent = 'Publicado! 💖'; location.href = d.redirect || '/'; return; }
        btn.disabled = false; btn.textContent = 'Publicar ♥'; prog.classList.add('hidden');
        erro.textContent = d.erro || (xhr.status === 413 ? 'Arquivo grande demais.' : 'Não consegui publicar. Tente de novo.');
        erro.classList.remove('hidden');
      };
      xhr.onerror = () => {
        btn.disabled = false; btn.textContent = 'Publicar ♥'; prog.classList.add('hidden');
        erro.textContent = 'Falha de conexão. Tente de novo.'; erro.classList.remove('hidden');
      };
      xhr.send(fd);
    });
  }
})();
