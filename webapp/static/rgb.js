let r = 0, g = 0, b = 0;

function updateRGBPreview() {
  const rgb = `rgb(${r}, ${g}, ${b})`;
  $('#color-preview').css('background-color', rgb);

  const showPercent = $('#toggle-units').prop('checked');

  // Display RGB
  $('#val-r').text(showPercent ? `${Math.round((r / 255) * 100)}%` : r);
  $('#val-g').text(showPercent ? `${Math.round((g / 255) * 100)}%` : g);
  $('#val-b').text(showPercent ? `${Math.round((b / 255) * 100)}%` : b);

  // Display HEX
  const hex = rgbToHex(r, g, b);
  $('#val-hex').text(hex);

  // HSV and HSL
  const [h, s, v] = rgbToHsv(r, g, b);
  const [h2, s2, l] = rgbToHsl(r, g, b);

  if (showPercent) {
    $('#val-hsv').text(`H: ${h}°, S: ${s}%, V: ${v}%`);
    $('#val-hsl').text(`H: ${h2}°, S: ${s2}%, L: ${l}%`);
  } else {
    $('#val-hsv').text(`H: ${Math.round((h / 360) * 100)}%, S: ${s}, V: ${v}`);
    $('#val-hsl').text(`H: ${Math.round((h2 / 360) * 100)}%, S: ${s2}, L: ${l}`);
  }

  drawHSVPolarPlot(h, s, v);
}

function rgbToHex(r, g, b) {
  return "#" + [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('').toUpperCase();
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, v = max;
  const d = max - min;
  s = max === 0 ? 0 : d / max;
  if (max === min) h = 0;
  else {
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h *= 60;
  }
  return [Math.round(h), Math.round(s * 100), Math.round(v * 100)];
}

function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;
  if (max === min) h = s = 0;
  else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      case b: h = (r - g) / d + 4; break;
    }
    h *= 60;
  }
  return [Math.round(h), Math.round(s * 100), Math.round(l * 100)];
}

function drawHSVPolarPlot(h, s, v) {
  const radius = s / 100;
  const angle = h;
  const rgb = `rgb(${r}, ${g}, ${b})`;

  const data = [{
    type: 'scatterpolar',
    r: [radius],
    theta: [angle],
    mode: 'markers',
    marker: {
      color: rgb,
      size: 18,
      line: { color: 'black', width: 1 }
    }
  }];

  const layout = {
    polar: {
      radialaxis: {
        visible: true,
        range: [0, 1],
        tickvals: [0.25, 0.5, 0.75, 1.0],
        ticktext: ['25%', '50%', '75%', '100%']
      },
      angularaxis: {
        rotation: 90,
        direction: "clockwise",
        tickvals: [0, 60, 120, 180, 240, 300],
        ticktext: ['Red', 'Yellow', 'Green', 'Cyan', 'Blue', 'Magenta']
      }
    },
    showlegend: false,
    margin: { t: 20, b: 20, l: 20, r: 20 }
  };

  Plotly.react('hsv-polar-plot', data, layout, { staticPlot: true });
}

function initRGBSlider(id, onSlide) {
  $(`#slider-${id}`).slider({
    orientation: "vertical",
    max: 255,
    value: 0,
    slide: function (event, ui) {
      onSlide(ui.value);
      updateRGBPreview();
    }
  });
}

$(document).ready(function () {
  initRGBSlider("r", val => r = val);
  initRGBSlider("g", val => g = val);
  initRGBSlider("b", val => b = val);
  $('#toggle-units').on('change', updateRGBPreview);
  updateRGBPreview();
});
