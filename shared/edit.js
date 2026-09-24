/**
 * 投资笔记编辑器 v4
 * 功能：文字编辑、图片插入/删除/替换、保存到Github、导出HTML
 */
(function() {
  'use strict';

  let isEditing = false;
  let savedRange = null;

  // ===== 工具函数 =====

  function saveSelection() {
    const sel = window.getSelection();
    if (sel.rangeCount > 0) {
      const range = sel.getRangeAt(0);
      if (range.startContainer.parentElement.closest('.container, .content, .article, main, article')) {
        savedRange = range.cloneRange();
      }
    }
  }

  function createImg(src) {
    const img = document.createElement('img');
    img.src = src;
    img.style.cssText = 'width:100%;border-radius:8px;margin:16px 0;box-shadow:0 2px 8px rgba(0,0,0,.1)';
    img.className = 'slide-img';
    return img;
  }

  function chooseAndInsert(insertFn) {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = 'image/*';
    input.onchange = (ev) => {
      const f = ev.target.files[0]; if (!f) return;
      const r = new FileReader();
      r.onload = (re) => insertFn(re.target.result);
      r.readAsDataURL(f);
    };
    input.click();
  }

  // ===== 主按钮栏 =====

  function createWrap() {
    ['__editWrap', '__editBtn', '__saveBtn', '__exportBtn', '__insertImgBtn'].forEach(id => {
      const old = document.getElementById(id);
      if (old) old.remove();
    });

    const wrap = document.createElement('div');
    wrap.id = '__editWrap';
    wrap.style.cssText = `
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      display: flex; flex-direction: column; gap: 10px; align-items: stretch;
    `;
    document.body.appendChild(wrap);

    const btn = document.createElement('button');
    btn.id = '__editBtn';
    btn.textContent = '✏️ 编辑';
    btn.style.cssText = btnStyle('#2b6cb0');
    btn.onclick = toggleEdit;
    wrap.appendChild(btn);
  }

  function btnStyle(bg) {
    return `
      background: ${bg}; color: #fff; border: none; border-radius: 24px;
      padding: 10px 24px; font-size: 14px; font-weight: 600; cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,.25); white-space: nowrap;
    `;
  }

  // ===== 获取可编辑元素 =====

  function getEditableEls() {
    const els = [];
    document.querySelectorAll('.container, .content, .article, main, article').forEach(ct => {
      ct.querySelectorAll('p, h1, h2, h3, h4, li, td, th, .callout, .callout-green, .callout-blue, .highlight, .key-point, .chapter, .subtitle, .meta, .knowledge-card').forEach(el => {
        if (el.closest('#__nav, nav, .nav, .navbar, .toc, #__editWrap')) return;
        els.push(el);
      });
    });
    return els;
  }

  // ===== 切换编辑模式 =====

  function toggleEdit() {
    isEditing = !isEditing;
    const btn = document.getElementById('__editBtn');
    const wrap = document.getElementById('__editWrap');

    if (isEditing) {
      btn.textContent = '✅ 完成编辑';
      btn.style.background = '#38a169';

      const els = getEditableEls();
      els.forEach(el => {
        el.contentEditable = 'true';
        el.style.outline = '1px dashed #2b6cb0';
        el.style.outlineOffset = '2px';
        el.style.position = el.style.position || 'relative';

        // 在文字块左侧加「+ 图片」小按钮
        if (!el.querySelector('.text-insert-img-btn')) {
          const plusBtn = document.createElement('button');
          plusBtn.className = 'text-insert-img-btn';
          plusBtn.textContent = '+图';
          plusBtn.style.cssText = `
            position: absolute; left: -36px; top: 2px;
            background: #805ad5; color: #fff; border: none;
            border-radius: 6px; padding: 2px 6px; font-size: 11px;
            cursor: pointer; z-index: 50; opacity: .8;
          `;
          plusBtn.title = '在这段后面插入图片';
          plusBtn.onclick = (e) => {
            e.preventDefault();
            chooseAndInsert((src) => {
              const img = createImg(src);
              el.parentNode.insertBefore(img, el.nextSibling);
            });
          };
          el.appendChild(plusBtn);
        }
      });

      document.addEventListener('selectionchange', saveSelection);

      // 给已有图片加操作按钮
      setupExistingImages();

      // 工具栏：插入图片
      addToolButton('__insertImgBtn', '🖼️ 插入图片', '#805ad5', () => {
        saveSelection();
        chooseAndInsert((src) => insertImageAtCursor(src));
      });

      // 工具栏：保存到Github
      addToolButton('__saveBtn', '☁️ 保存到云端', '#3182ce', saveToGithub);

      // 工具栏：导出HTML
      addToolButton('__exportBtn', '📥 导出HTML', '#d69e2e', exportHTML);

    } else {
      btn.textContent = '✏️ 编辑';
      btn.style.background = '#2b6cb0';
      document.removeEventListener('selectionchange', saveSelection);
      savedRange = null;

      document.querySelectorAll('[contenteditable]').forEach(el => {
        el.contentEditable = 'false';
        el.style.outline = 'none';
      });
      document.querySelectorAll('.text-insert-img-btn, .img-remove-btn, .img-insertafter-btn').forEach(el => el.remove());
      ['__insertImgBtn', '__saveBtn', '__exportBtn'].forEach(id => {
        const el = document.getElementById(id); if (el) el.remove();
      });
    }
  }

  function addToolButton(id, text, bg, onclick) {
    if (document.getElementById(id)) return;
    const b = document.createElement('button');
    b.id = id; b.textContent = text;
    b.style.cssText = btnStyle(bg);
    b.onclick = onclick;
    document.getElementById('__editWrap').appendChild(b);
  }

  function setupExistingImages() {
    document.querySelectorAll('img').forEach(img => {
      if (img.closest('#__nav, nav, .nav, .navbar, #__editWrap, .img-remove-btn')) return;

      // 检查是否已经包装过
      if (img.parentNode.classList && img.parentNode.classList.contains('img-wrapper')) return;

      const w = document.createElement('div');
      w.className = 'img-wrapper';
      w.style.position = 'relative';
      img.parentNode.insertBefore(w, img);
      w.appendChild(img);

      // 删除按钮
      const rb = document.createElement('button');
      rb.className = 'img-remove-btn';
      rb.textContent = '✕ 删除';
      rb.style.cssText = `
        position: absolute; top: 8px; right: 8px;
        background: #e53e3e; color: #fff; border: none;
        border-radius: 6px; padding: 4px 10px; font-size: 12px;
        cursor: pointer; z-index: 100;
      `;
      rb.onclick = (e) => { e.preventDefault(); if (confirm('删除这张图片？')) w.remove(); };
      w.appendChild(rb);

      // 在后插入按钮
      const ib = document.createElement('button');
      ib.className = 'img-insertafter-btn';
      ib.textContent = '+ 在后插入';
      ib.style.cssText = `
        position: absolute; top: 8px; left: 8px;
        background: #805ad5; color: #fff; border: none;
        border-radius: 6px; padding: 4px 10px; font-size: 12px;
        cursor: pointer; z-index: 100;
      `;
      ib.onclick = (e) => {
        e.preventDefault();
        chooseAndInsert((src) => {
          const newImg = createImg(src);
          w.parentNode.insertBefore(newImg, w.nextSibling);
        });
      };
      w.appendChild(ib);

      // 双击替换
      img.style.cursor = 'pointer';
      img.title = '双击替换图片';
      img.ondblclick = (e) => {
        e.preventDefault();
        chooseAndInsert((src) => { img.src = src; });
      };
    });
  }

  function insertImageAtCursor(src) {
    const img = createImg(src);
    if (!savedRange) {
      const container = document.querySelector('.container') || document.body;
      container.appendChild(img);
      return;
    }
    let node = savedRange.startContainer;
    if (node.nodeType === 3) node = node.parentElement;
    const block = node.closest('p, h1, h2, h3, h4, li, td, div, .chapter, .section, .callout, .highlight, .key-point');
    if (block) {
      block.parentNode.insertBefore(img, block.nextSibling);
    } else {
      savedRange.insertNode(img);
    }
  }

  // ===== 云端保存（经服务端 /api/note-save 提交到 Github，token 不接触浏览器）=====

  // 在 DOM 克隆体上移除编辑辅助 UI、解包图片容器，得到干净 HTML，不影响当前编辑页
  function buildCleanHtml() {
    const clone = document.documentElement.cloneNode(true);
    const doc = clone.ownerDocument;

    clone.querySelectorAll(
      '#__editWrap, .text-insert-img-btn, .img-remove-btn, .img-insertafter-btn'
    ).forEach(n => n.remove());

    // 解开 .img-wrapper 包裹，把图片放回原始位置（丢弃删除/插入按钮）
    clone.querySelectorAll('.img-wrapper').forEach(w => {
      const frag = doc.createDocumentFragment();
      Array.from(w.childNodes).forEach(ch => {
        if (ch.nodeType === 1 && ch.classList &&
            (ch.classList.contains('img-remove-btn') ||
             ch.classList.contains('img-insertafter-btn'))) return;
        frag.appendChild(ch);
      });
      w.parentNode.replaceChild(frag, w);
    });

    clone.querySelectorAll('[contenteditable]').forEach(n => {
      n.removeAttribute('contenteditable');
      n.style.outline = '';
    });

    return '<!DOCTYPE html>\n' + clone.outerHTML;
  }

  function currentRepoPath() {
    let p = window.location.pathname.replace(/^\//, '').replace(/\/$/, '');
    if (!/\.html$/.test(p)) p = p + '/index.html';
    return p;
  }

  function saveToGithub() {
    let key = localStorage.getItem('note_edit_key');
    if (!key) {
      const t = prompt('请输入编辑密钥 EDIT_KEY（只需输入一次，保存在本浏览器）：');
      if (!t) return;
      key = t.trim();
      localStorage.setItem('note_edit_key', key);
    }

    const path = currentRepoPath();
    if (!/^learn\//.test(path)) {
      alert('当前页面不在可保存的笔记目录（learn/）内。');
      return;
    }

    const btn = document.getElementById('__saveBtn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ 保存中…'; }

    fetch('/api/note-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, path, content: buildCleanHtml() })
    })
    .then(r => r.json())
    .then(data => {
      if (data.unchanged) {
        alert('内容没有变化，无需保存。');
      } else if (data.ok) {
        let msg = '已保存！';
        if (data.images) msg += ' 新上传图片 ' + data.images + ' 张。';
        msg += '\n正在刷新以显示最新内容…';
        alert(msg);
        // KV 即时覆盖已写入，刷新后立即展示最新版本，无需等待部署
        setTimeout(() => location.reload(), 500);
      } else {
        if (data.error === '编辑密钥错误') localStorage.removeItem('note_edit_key');
        throw new Error(data.error || '保存失败');
      }
    })
    .catch(err => alert('保存失败：' + err.message))
    .finally(() => {
      if (btn) { btn.disabled = false; btn.textContent = '☁️ 保存到云端'; }
    });
  }

  // ===== 导出HTML =====

  function exportHTML() {
    document.querySelectorAll('.text-insert-img-btn, .img-remove-btn, .img-insertafter-btn').forEach(el => el.remove());
    const html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
    const blob = new Blob([html], {type: 'text/html;charset=utf-8'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'index.html'; a.click();
    URL.revokeObjectURL(url);
    alert('HTML已导出。');
  }

  // ===== 初始化 =====

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createWrap);
  } else {
    createWrap();
  }
})();
