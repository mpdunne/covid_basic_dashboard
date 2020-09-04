function appendToSlider() {
    var flag = document.getElementById('output-container-range-slider');
    document.querySelector('#slider-wrapper .rc-slider-handle').appendChild(flag);
    flag.style.display = 'block';  // Make visible after moving
  }
  
  setTimeout(appendToSlider, 2000);