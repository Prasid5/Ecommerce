function slide(btn, direction) {
    const section = btn.closest(".category-section");
    const grid = section.querySelector(".product-grid");
    const cardWidth = grid.querySelector(".product-card").offsetWidth + 32; // card + gap
    grid.scrollBy({
        left: direction * cardWidth,
        behavior: "smooth"
    });
}