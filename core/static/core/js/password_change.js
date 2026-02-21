const COMMON = [
  "123456", "password", "12345678", "qwerty", "abc123", "111111",
  "123123", "admin", "letmein", "welcome", "monkey", "dragon",
  "master", "1234567", "123456789", "iloveyou", "sunshine",
  "princess", "football", "shadow"
];

const input = document.getElementById("id_new_password1");
const bars = [
  document.getElementById("bar1"),
  document.getElementById("bar2"),
  document.getElementById("bar3"),
];
const label = document.getElementById("strengthLabel");
const hints = {
  length:  document.getElementById("hint-length"),
  numeric: document.getElementById("hint-numeric"),
  common:  document.getElementById("hint-common"),
  similar: document.getElementById("hint-similar"),
};

function setHint(el, ok) {
  el.classList.toggle("pwd-hint--ok", ok);
}

function resetBars() {
  bars.forEach(b => { b.className = "pwd-strength__bar"; });
}

input.addEventListener("input", () => {
  const val = input.value;

  const okLength  = val.length >= 8;
  const okNumeric = !/^\d+$/.test(val);
  const okCommon  = !COMMON.includes(val.toLowerCase());
  const okSimilar = val.length === 0 || !val.toLowerCase().includes(USERNAME.toLowerCase());

  setHint(hints.length,  okLength);
  setHint(hints.numeric, okNumeric);
  setHint(hints.common,  okCommon);
  setHint(hints.similar, okSimilar);

  const score = [okLength, okNumeric, okCommon, okSimilar].filter(Boolean).length;

  resetBars();

  if (val.length === 0) {
    label.textContent = "";
    return;
  }

  if (score <= 2) {
    bars[0].classList.add("pwd-strength__bar--weak");
    label.style.color = "rgba(255,80,90,0.8)";
    label.textContent = "Débil";
  } else if (score === 3) {
    bars[0].classList.add("pwd-strength__bar--medium");
    bars[1].classList.add("pwd-strength__bar--medium");
    label.style.color = "rgba(251,191,36,0.8)";
    label.textContent = "Media";
  } else {
    bars.forEach(b => b.classList.add("pwd-strength__bar--strong"));
    label.style.color = "rgba(110,231,255,0.85)";
    label.textContent = "Fuerte ✓";
  }
});