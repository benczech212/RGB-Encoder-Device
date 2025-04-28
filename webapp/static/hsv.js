let h = 0, s = 100, v = 100;

function hsvToRgb(h, s, v) {
  s /= 100;
  v /= 100;

  let c = v * s;
  let x = c * (1 - Math.abs((h / 60) % 2 - 1));
  let m = v - c;
  let r1, g1, b1;

  if (h < 60) [r1, g1, b1] = [c, x, 0];
  else if (h < 120) [r1, g1, b1] = [x, c, 0];
  else if (h < 180) [r1, g1, b1] = [0, c, x];
  else if (h < 240) [r1, g1, b1] = [0, x, c];
  else if (h < 300) [r1, g1, b1] = [x, 0, c];
  else [r1, g1, b1] = [c, 0, x];

  let r = Math.round((r1 + m) * 255);
  let g = Math.round((g1 + m) * 255);
  let b = Math.round((b1 + m) * 255);

  return `rgb(${r}, ${g}, ${b})`;
}

function updateHSVPreview() {
  $('#color-preview').css('background-color', hsvToRgb(h, s, v));
}

$(document).ready(function () {
  $("#slider-h").slider({
    orientation: "vertical",
    max: 360,
    value: 0,
    slide: function (event, ui) {
      h = ui.value;
      updateHSVPreview();
    }
  });

  $("#slider-s").on("input", function () {
    s = parseInt(this.value);
    updateHSVPreview();
  });

  $("#slider-v").on("input", function () {
    v = parseInt(this.value);
    updateHSVPreview();
  });

  updateHSVPreview();
});
