(() => {
  const enhance = () => {
    if (document.querySelector(".book-lightbox")) return;

    const dialog = document.createElement("dialog");
    dialog.className = "book-lightbox";
    dialog.innerHTML =
      '<button class="book-lightbox__close" type="button" aria-label="关闭图形预览">关闭</button>' +
      '<div class="book-lightbox__content"></div>';
    document.body.append(dialog);

    const content = dialog.querySelector(".book-lightbox__content");
    const close = dialog.querySelector(".book-lightbox__close");
    const closeDialog = () => dialog.close();
    close.addEventListener("click", closeDialog);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeDialog();
    });
    dialog.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDialog();
    });

    document.querySelectorAll(".book-diagram img, .md-typeset .mermaid svg").forEach((image) => {
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
    });
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(enhance);
  } else {
    document.addEventListener("DOMContentLoaded", enhance);
  }
})();
