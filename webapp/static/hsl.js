let h = 0, s = 100, l = 50;

function updateHSLPreview() {
  const hsl = `hsl(${h}, ${s}%, ${l}%)`;
  $('#color-preview').css('background-color', hsl);
}

$(document).ready(function () {
  $("#slider-h").slider({
    orientation: "vertical",
    max: 360,
    value: 0,
    slide: function (event, ui) {
      h = ui.value;
      updateHSLPreview();
    }
  });

  $("#slider-s").on("input", function () {
    s = parseInt(this.value);
    updateHSLPreview();
  });

  $("#slider-l").on("input", function () {
    l = parseInt(this.value);
    updateHSLPreview();
  });

  updateHSLPreview();
});
