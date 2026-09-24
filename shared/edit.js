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
      addToolButton('__saveBtn', '☁️ 保存到Github', '#3182ce', saveToGithub);

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

  // ===== Github保存 =====

  function saveToGithub() {
    const token = localStorage.getItem('github_token');
    if (!token) {
      const t = prompt('请输入你的Github Personal Access Token（需要repo权限，只会保存在你浏览器本地）：');
      if (!t) return;
      localStorage.setItem('github_token', t.trim());
    }

    // 获取当前文件在仓库中的路径
    let path = window.location.pathname;
    // 去掉开头的/，去掉末尾的/（目录形式访问，对应index.html）
    path = path.replace(/^\//, '').replace(/\/$/, '');
    if (!path.endsWith('.html')) path = path + '/index.html';
    if (!path) path = 'index.html';

    const repo = 'SugieLiao/invest';
    const apiUrl = `https://api.github.com/repos/${repo}/contents/${path}`;

    // 先获取当前文件的sha
    fetch(apiUrl, {
      headers: { 'Authorization': 'token ' + localStorage.getItem('github_token') }
    })
    .then(r => r.json())
    .then(data => {
      if (data.message && data.message !== 'Not Found') {
        throw new Error(data.message);
      }

      // 获取当前页面HTML（去掉编辑状态）
      document.querySelectorAll('.text-insert-img-btn, .img-remove-btn, .img-insertafter-btn').forEach(el => el.remove());
      const html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
      // 恢复编辑按钮（重新进入编辑模式）
      const content = btoa(unescape(encodeURIComponent(html)));

      const body = {
        message: '更新笔记: ' + path,
        content: content,
        branch: 'main'
      };
      if (data.sha) body.sha = data.sha;

      return fetch(apiUrl, {
        method: 'PUT',
        headers: {
          'Authorization': 'token ' + localStorage.getItem('github_token'),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });
    })
    .then(r => r.json())
    .then(data => {
      if (data.commit) {
        alert('已保存到Github！提交: ' + data.commit.sha.substring(0, 7) + '\nCloudflare Pages会自动部署，稍等1-2分钟线上即更新。');
      } else {
        throw new Error(data.message || '保存失败');
      }
    })
    .catch(err => {
      alert('保存失败: ' + err.message + '\n请检查token是否正确、是否有repo权限。');
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
