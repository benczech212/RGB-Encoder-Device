let h = 0, s = 100, l = 50;

function updateColorUI() {
  const hsl = `hsl(${h}, ${s}%, ${l}%)`;
  $('#color-preview').css('background-color', hsl);
  $('#submit-button').css('background-color', hsl);
}

function initSlider(id, max, initialValue, onSlide) {
  $(`#slider-${id}`).slider({
    orientation: "vertical",
    max: max,
    value: initialValue,
    slide: function (event, ui) {
      onSlide(ui.value);
      updateColorUI();
    }
  });
}

$(document).ready(function () {
  initSlider("h", 360, h, (val) => h = val);
  initSlider("s", 100, s, (val) => s = val);
  initSlider("l", 100, l, (val) => l = val);

  updateColorUI();

  $('#colorForm').on('submit', function (e) {
    e.preventDefault();
    $.post('/set_color', { h, s, l }, function (data) {
      console.log('Color sent:', data);
    });
  });
});
