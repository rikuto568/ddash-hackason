console.log("JS読み込まれた");

const btn = document.getElementById("btn");

btn.addEventListener("click", () => {
  console.log("クリックされた");
  window.location.href = "app.html";
});
