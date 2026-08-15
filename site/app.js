const count = document.getElementById('cartCount');
let items = 0;
document.querySelectorAll('[data-add]').forEach((button) => {
  button.addEventListener('click', () => {
    items += 1;
    count.textContent = new Intl.NumberFormat('fa-IR').format(items);
    button.textContent = 'به سبد اضافه شد ✓';
    setTimeout(() => { button.textContent = 'افزودن به سبد'; }, 1400);
  });
});
document.getElementById('cartButton').addEventListener('click', () => {
  alert(`تعداد کالاهای سبد: ${new Intl.NumberFormat('fa-IR').format(items)}`);
});
