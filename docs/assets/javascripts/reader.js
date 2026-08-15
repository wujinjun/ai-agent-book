(() => {
  const enhance = () => {
    let dialog = document.querySelector(".book-lightbox");
    if (!dialog) {
      dialog = document.createElement("dialog");
      dialog.className = "book-lightbox";
      dialog.innerHTML =
        '<button class="book-lightbox__close" type="button" aria-label="关闭图形预览">关闭</button>' +
        '<div class="book-lightbox__content"></div>';
      document.body.append(dialog);
    }

    const content = dialog.querySelector(".book-lightbox__content");
    const close = dialog.querySelector(".book-lightbox__close");
    const closeDialog = () => dialog.close();
    if (!dialog.dataset.bookReady) {
      close.addEventListener("click", closeDialog);
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) closeDialog();
      });
      dialog.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeDialog();
      });
      dialog.dataset.bookReady = "true";
    }

    document
      .querySelectorAll(
        '.book-diagram img, .md-typeset .mermaid svg, .md-typeset img[src*="/infographics/"]',
      )
      .forEach((image) => {
        if (image.dataset.bookZoomReady) return;
        image.setAttribute("tabindex", "0");
        image.setAttribute("role", "button");
        image.setAttribute("aria-label", "放大查看图形");
        const open = () => {
          content.replaceChildren(image.cloneNode(true));
          dialog.showModal();
          close.focus();
        };
        image.addEventListener("click", open);
        image.addEventListener("keydown", (event) => {
          if (event.key === "Enter" || event.key === " ") open();
        });
        image.dataset.bookZoomReady = "true";
      });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", enhance);
  } else {
    enhance();
  }
  if (typeof document$ !== "undefined") {
    document$.subscribe(() => requestAnimationFrame(enhance));
  }
  const observer = new MutationObserver(() => requestAnimationFrame(enhance));
  observer.observe(document.body, { childList: true, subtree: true });
})();
