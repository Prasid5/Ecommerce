function increaseQty(button) {
  const input = button.previousElementSibling;
  let val = parseInt(input.value);
  input.value = val + 1;
  updateTotals();
}

function decreaseQty(button) {
  const input = button.nextElementSibling;
  let val = parseInt(input.value);
  if (val > 1) {
    input.value = val - 1;
    updateTotals();
  }
}

function updateTotals() {
  const qty = parseInt(document.querySelector('.qty-input').value);
  const price = 1399;
  document.querySelector('.item-amount').innerText = `Rs.${(qty * price).toFixed(2)}`;
  document.querySelector('.subtotal').innerText = `Rs.${(qty * price).toFixed(2)}`;
}
