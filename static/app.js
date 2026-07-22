var dataByDate = {};
var currentDate = null;
var currentCategory = "all";
var DATA_URL = "data/index.json";

async function init() {
  try {
    var resp = await fetch(DATA_URL);
    dataByDate = await resp.json();
    var dates = Object.keys(dataByDate).sort().reverse();
    if (dates.length === 0) { showEmpty(); return; }
    currentDate = dates[0];
    renderDateNav(dates);
    renderDay(currentDate);
    showQrFallback();
  } catch(e) {
    showEmpty();
  }
}

function showQrFallback() {
  var el = document.getElementById("qrBox");
  if (!el) return;
  el.innerHTML = "";
  var size = 80;
  var canvas = document.createElement("canvas");
  canvas.width = size; canvas.height = size;
  var ctx = canvas.getContext("2d");
  var qr = encodeQr(window.location.href);
  var mod = size / qr.length;
  ctx.fillStyle = "#1a1a2e";
  for (var y = 0; y < qr.length; y++)
    for (var x = 0; x < qr[y].length; x++)
      if (qr[y][x]) ctx.fillRect(x*mod, y*mod, mod, mod);
  el.appendChild(canvas);
  var urlEl = document.getElementById("qrUrl");
  if (urlEl) urlEl.textContent = window.location.href.replace("https://","").replace("http://","");
}

function encodeQr(text) {
  var size = 21, m = [];
  for (var i=0;i<size;i++) { m[i]=[]; for(var j=0;j<size;j++) m[i][j]=false; }
  function finder(r,c) {
    for(var rr=r;rr<r+7;rr++) for(var cc=c;cc<c+7;cc++)
      m[rr][cc]=(rr===r||rr===r+6||cc===c||cc===c+6)||(rr>=r+2&&rr<=r+4&&cc>=c+2&&cc<=c+4);
  }
  finder(0,0); finder(0,14); finder(14,0);
  for(var i=8;i<13;i++){m[6][i]=i%2===0;m[i][6]=i%2===0;}
  var data=[];
  for(var i=0;i<text.length;i++) data.push(text.charCodeAt(i)%2);
  var dx=0;
  for(var r=8;r<21&&dx<data.length;r++)
    for(var c=8;c<21&&dx<data.length;c++) {
      if(r===6||c===6||(r>=0&&r<8&&(c>=0&&c<8||c>=14))||(r>=14&&c>=0&&c<8)) continue;
      m[r][c]=data[dx++];
    }
  return m;
}

function renderDateNav(dates) {
  var nav = document.createElement("nav");
  nav.className = "date-nav";
  dates.forEach(function(d) {
    var chip = document.createElement("span");
    chip.className = "date-chip" + (d===currentDate?" active":"");
    chip.textContent = formatDate(d);
    chip.onclick = function(){
      currentDate = d;
      document.querySelectorAll(".date-chip").forEach(function(c){c.classList.remove("active")});
      chip.classList.add("active");
      renderDay(d);
    };
    nav.appendChild(chip);
  });
  var app = document.getElementById("app");
  if (app.firstChild) app.insertBefore(nav, app.firstChild);
  else app.appendChild(nav);
}

function renderDay(date) {
  var day = dataByDate[date];
  if (!day) return;
  var drEl = document.getElementById("dateRange");
  var tcEl = document.getElementById("tweetCount");
  var utEl = document.getElementById("updateTime");
  if (drEl) drEl.textContent = day.meta.dateRange;
  if (tcEl) tcEl.textContent = day.tweets.length + " ???";
  if (utEl) utEl.textContent = day.meta.generatedAt || "?";
  renderSummary(day.summary);
  renderFilters(day.categories);
  renderTweets(day.tweets);
}

function renderSummary(summary) {
  var body = document.getElementById("summaryBody");
  if (!body) return;
  body.className = "summary-body summary-text";
  if (!summary) { body.innerHTML = "<p>????</p>"; return; }
  var html = summary.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>");
  html = html.split("\n").filter(function(l){return l.trim()}).map(function(l){
    return "<p>" + l.replace(/^- */,"? ") + "</p>";
  }).join("");
  body.innerHTML = html;
}

function renderFilters(categories) {
  var filters = document.getElementById("filters");
  if (!filters) return;
  var cats = ["all"].concat(categories.map(function(c){return c.name}));
  filters.innerHTML = cats.map(function(c){
    var label = c==="all"?"??":c;
    var cls = c===currentCategory?" active":"";
    return "<span class=\"filter-chip" + cls + "\" onclick=\"filterTweets('" + c + "')\">" + label + "</span>";
  }).join("");
}

function filterTweets(cat) {
  currentCategory = cat;
  document.querySelectorAll(".filter-chip").forEach(function(chip){
    chip.classList.toggle("active", chip.textContent===cat||(cat==="all"&&chip.textContent==="??"));
  });
  renderTweets(dataByDate[currentDate].tweets);
}

function renderTweets(tweets) {
  var grid = document.getElementById("tweetsGrid");
  if (!grid) return;
  var filtered = currentCategory==="all"?tweets:tweets.filter(function(t){return t.category===currentCategory});
  if (filtered.length===0) {
    grid.innerHTML = "<div class=\"empty-state\"><div class=\"icon\">??</div><p>????????</p></div>";
    return;
  }
  grid.innerHTML = filtered.map(function(t,i){
    var time = new Date(t.time).toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"});
    return "<div class=\"tweet-card\" id=\"tweet-" + i + "\" onclick=\"toggleTweet(" + i + ")\">" +
      "<div class=\"tweet-card-header\">" +
        "<span class=\"tweet-card-title\">" + escapeHtml(t.title) + "</span>" +
        "<span class=\"tweet-card-category\">" + escapeHtml(t.category||"") + "</span>" +
        "<span class=\"tweet-card-time\">" + time + "</span>" +
        "<span class=\"arrow\">?</span>" +
      "</div>" +
      "<div class=\"tweet-card-body\">" + escapeHtml(t.text) + "</div>" +
    "</div>";
  }).join("");
}

function toggleTweet(i) {
  var card = document.getElementById("tweet-"+i);
  if (card) card.classList.toggle("expanded");
}

function formatDate(d) {
  var p = d.split("-");
  return p[1] + "/" + p[2];
}

function escapeHtml(t) {
  var d = document.createElement("div");
  d.textContent = t;
  return d.innerHTML;
}

function showEmpty() {
  var drEl = document.getElementById("dateRange");
  var tcEl = document.getElementById("tweetCount");
  var sbEl = document.getElementById("summaryBody");
  var tgEl = document.getElementById("tweetsGrid");
  if (drEl) drEl.textContent = "????";
  if (tcEl) tcEl.textContent = "";
  if (sbEl) sbEl.innerHTML = "<div class=\"loading\">?????????????????</div>";
  if (tgEl) tgEl.innerHTML = "<div class=\"empty-state\"><div class=\"icon\">??</div><p>???????</p></div>";
}

init();
