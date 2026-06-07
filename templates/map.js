// ═══════════════════════════════════════════════════
// map.js — 线段碰撞检测（路线用线段而非散点）
// ═══════════════════════════════════════════════════

var map = L.map('map', { center: [{{CENTER_LAT}}, {{CENTER_LNG}}], zoom: 7, zoomControl: true, scrollWheelZoom: true });
L.tileLayer('{{TILE_URL}}', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>', subdomains: 'abcd', maxZoom: 20 }).addTo(map);

var standardTile = L.tileLayer('{{TILE_URL}}', { attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>', subdomains: 'abcd', maxZoom: 20 });
var terrainTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', { attribution: 'Tiles &copy; Esri', maxZoom: 17 });
standardTile.addTo(map);
document.querySelectorAll('.ls-btn').forEach(function(btn) {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.ls-btn').forEach(function(b) { b.classList.remove('active'); });
    this.classList.add('active');
    if (this.dataset.layer === 'standard') { map.removeLayer(terrainTile); standardTile.addTo(map); }
    else { map.removeLayer(standardTile); terrainTile.addTo(map); }
  });
});

// ── 文字测量 ──
var _mc = null, _mx = null;
function mw(txt, s) {
  if (!_mx) { _mc = document.createElement('canvas'); _mx = _mc.getContext('2d'); }
  _mx.font = s + 'px "Noto Sans SC", system-ui, sans-serif';
  return Math.round(_mx.measureText(txt).width);
}

// ── 路线（主路线 + 支线 + 端线段数据）──
for (var i = 0; i < mainRoutes.length; i++)
  L.polyline(mainRoutes[i][1], { color: mainRoutes[i][0], weight: 4, opacity: 0.85, smoothFactor: 1 }).addTo(map);
var spurLayer = L.layerGroup();

// 预采样路线线段（每 5 个点取一段），用于像素碰撞
var routeSegData = [];
function collectSegs(arr) {
  for (var i = 0; i < arr.length; i++) {
    var poly = arr[i][1];
    for (var j = 0; j + 1 < poly.length; j += 5)
      routeSegData.push([poly[j], poly[j+1]]);
  }
}
collectSegs(mainRoutes);
collectSegs(spurRoutes);

// ── 线段-矩形 相交检测 ──
function segHitRect(x1,y1,x2,y2,l,r,t,b) {
  function inside(px,py) { return px>=l&&px<=r&&py>=t&&py<=b; }
  if (inside(x1,y1)||inside(x2,y2)) return true;
  function segInt(ax1,ay1,ax2,ay2,bx1,by1,bx2,by2) {
    var dx1=ax2-ax1,dy1=ay2-ay1,dx2=bx2-bx1,dy2=by2-by1;
    var cr = dx1*dy2-dy1*dx2;
    if (Math.abs(cr)<1e-9) return false;
    var t2=((bx1-ax1)*dy2-(by1-ay1)*dx2)/cr;
    var u=((bx1-ax1)*dy1-(by1-ay1)*dx1)/cr;
    return t2>=0&&t2<=1&&u>=0&&u<=1;
  }
  return segInt(x1,y1,x2,y2,l,t,r,t)||segInt(x1,y1,x2,y2,l,b,r,b)||
         segInt(x1,y1,x2,y2,l,t,l,b)||segInt(x1,y1,x2,y2,r,t,r,b);
}

// ── 城市圆点 ──
var dotLayer = L.layerGroup().addTo(map);
for (var i = 0; i < cityPosData.length; i++) {
  var c = cityPosData[i];
  dotLayer.addLayer(L.circleMarker([c.lat, c.lng], { radius: 5, color: c.color, weight: 2.5, fillColor: '#fff', fillOpacity: 1 }));
}

// ── 标签图层 ──
var labelLayer = L.layerGroup().addTo(map);
var leadLayer = L.layerGroup().addTo(map);

// ── POI ──
var poiMajor = L.layerGroup();
var poiMinor = L.layerGroup();
for (var i = 0; i < majorSpots.length; i++) {
  var s = majorSpots[i];
  poiMajor.addLayer(L.marker([s[0], s[1]], { icon: L.divIcon({ className: '', html: '<div style="display:flex;align-items:center;gap:3px;"><div style="width:6px;height:6px;background:'+s[2]+';border-radius:50%;flex-shrink:0;"></div><span style="font-size:12px;font-weight:700;color:'+s[2]+';white-space:nowrap;">'+s[3]+'</span></div>', iconSize: [40,28], iconAnchor: [s[4]+20, s[5]+14] }) }));
}
for (var i = 0; i < spots.length; i++) {
  var s = spots[i];
  poiMinor.addLayer(L.marker([s[0], s[1]], { icon: L.divIcon({ className: '', html: '<div style="display:flex;align-items:center;gap:3px;"><div style="width:6px;height:6px;background:#3d7a4a;border-radius:50%;flex-shrink:0;"></div><span style="font-size:11px;font-weight:700;color:#3d7a4a;white-space:nowrap;">'+s[2]+'</span></div>', iconSize: [80,18], iconAnchor: [4,9] }) }));
}

// ── 配置 ──
var CFG = [
  { zMin:0, zMax:99, basePx:28, compact:true, lead:true },
];
var DIRS = [[1,0],[-1,0],[0,-1],[0,1],[1,-1],[-1,-1],[1,1],[-1,1]];

// ── 碰撞检测（线段级：城市全检 / Dx不检路线）──
function hasOverlap(cx, cy, w, h, segPx, dp, boxes, checkRoutes) {
  var hw = w/2, hh = h/2, l=cx-hw, r=cx+hw, t=cy-hh, b=cy+hh;
  if (checkRoutes) {
    for (var i=0;i<segPx.length;i++)
      if (segHitRect(segPx[i].x1,segPx[i].y1,segPx[i].x2,segPx[i].y2,l,r,t,b)) return true;
  }
  // 圆点
  for (var i=0;i<dp.length;i++)
    if (dp[i].x>=l-7&&dp[i].x<=r+7&&dp[i].y>=t-7&&dp[i].y<=b+7) return true;
  // 已放标签
  for (var i=0;i<boxes.length;i++) {
    var o=boxes[i];
    if (l<o.r&&r>o.l&&t<o.b&&b>o.t) return true;
  }
  return false;
}

// ── 搜索无碰撞位置 ──
// checkRoutes: true=城市（全检）, false=Dx（不检路线）
function findPos(lat,lng,basePx,w,h,segPx,dp,boxes,checkRoutes) {
  var org = map.latLngToLayerPoint(L.latLng(lat,lng));
  var hw = w/2, hh = h/2;
  var sc = [1,1.5,2,2.5,3];
  for (var si=0;si<sc.length;si++) {
    var d = basePx*sc[si];
    for (var di=0;di<DIRS.length;di++) {
      var cx=org.x+DIRS[di][0]*d, cy=org.y+DIRS[di][1]*d;
      if (!hasOverlap(cx,cy,w,h,segPx,dp,boxes,checkRoutes)) {
        var ll = map.layerPointToLatLng(L.point(cx,cy));
        return {lat:ll.lat,lng:ll.lng,box:{l:cx-hw,r:cx+hw,t:cy-hh,b:cy+hh}};
      }
    }
  }
  // fallback: 3×basePx 中最优方向
  var best=null, bestSc=-Infinity;
  for (var di=0;di<DIRS.length;di++) {
    var cx=org.x+DIRS[di][0]*basePx*3, cy=org.y+DIRS[di][1]*basePx*3;
    var minR=checkRoutes?Infinity:999, minD=Infinity;
    if (checkRoutes) {
      for (var i=0;i<segPx.length;i++) {
        var mx=(segPx[i].x1+segPx[i].x2)/2, my=(segPx[i].y1+segPx[i].y2)/2;
        var dd=(cx-mx)*(cx-mx)+(cy-my)*(cy-my);
        if (dd<minR) minR=dd;
      }
    }
    for (var i=0;i<dp.length;i++) {
      var dd=(cx-dp[i].x)*(cx-dp[i].x)+(cy-dp[i].y)*(cy-dp[i].y);
      if (dd<minD) minD=dd;
    }
    for (var i=0;i<boxes.length;i++) {
      var o=boxes[i];
      if (cx>=o.l-10&&cx<=o.r+10&&cy>=o.t-10&&cy<=o.b+10) minD=0;
    }
    if (Math.sqrt(minR)+Math.sqrt(minD)>bestSc) {
      bestSc = Math.sqrt(minR)+Math.sqrt(minD);
      best = {cx:cx,cy:cy};
    }
  }
  if (best) {
    var ll = map.layerPointToLatLng(L.point(best.cx,best.cy));
    return {lat:ll.lat,lng:ll.lng,box:{l:best.cx-hw,r:best.cx+hw,t:best.cy-hh,b:best.cy+hh}};
  }
  return {lat:lat,lng:lng,box:{l:0,r:0,t:0,b:0}};
}

// ── 标签工厂 ──
function mkCity(lat,lng,color,name) {
  return L.marker([lat,lng],{icon:L.divIcon({className:'',html:'<span style="display:inline-block;color:'+color+';font-size:14px;font-weight:700;white-space:nowrap;text-shadow:0 0 4px #fff,0 0 8px #fff;">'+name+'</span>',iconSize:null,iconAnchor:[Math.round(mw(name,14)/2),10]})});
}
function mkDx(lat,lng,color,name,sub,dist) {
  var lbl='<div style="text-align:center;line-height:1.3;white-space:nowrap;"><div style="font-weight:700;font-size:12px;color:'+color+';text-shadow:0 0 4px #fff,0 0 8px #fff;">'+name+'</div>';
  if (sub) lbl+='<div style="font-size:10px;color:'+color+';text-shadow:0 0 4px #fff,0 0 8px #fff;">'+sub+'</div>';
  lbl+='<div style="font-size:10px;color:#7a7258;text-shadow:0 0 4px #fff,0 0 8px #fff;">'+dist+'</div></div>';
  return L.marker([lat,lng],{icon:L.divIcon({className:'',html:lbl,iconSize:[80,36],iconAnchor:[40,18]})});
}
function mkDxC(lat,lng,color,name) {
  return L.marker([lat,lng],{icon:L.divIcon({className:'',html:'<div style="font-weight:700;font-size:11px;color:'+color+';text-shadow:0 0 4px #fff,0 0 8px #fff;">'+name+'</div>',iconSize:null,iconAnchor:[20,8]})});
}
function mkLead(fLat,fLng,tLat,tLng,color) {
  return L.polyline([[fLat,fLng],[tLat,tLng]],{color:color,weight:1.5,opacity:0.3,dashArray:'4,4'});
}

// ── fitBounds ──
var ab = L.latLngBounds(cityPosData[0]?[cityPosData[0].lat,cityPosData[0].lng]:[0,0]);
function extA(arr){for(var i=0;i<arr.length;i++)ab.extend(arr[i]);}
for(var i=0;i<mainRoutes.length;i++) extA(mainRoutes[i][1]);
for(var i=0;i<spurRoutes.length;i++) extA(spurRoutes[i][1]);
cityPosData.forEach(function(c){ab.extend([c.lat,c.lng]);});
dxData.forEach(function(d){ab.extend([d.lat,d.lng]);});
majorSpots.forEach(function(s){ab.extend([s[0],s[1]]);});
spots.forEach(function(s){ab.extend([s[0],s[1]]);});
map.fitBounds(ab,{padding:[50,50]});

// ── Zoom 处理器 ──
function u() {
  var z = map.getZoom();
  document.getElementById('zoom-display').textContent = 'Zoom ' + z;
  
  var cfg = CFG[0];
  for (var ci=0;ci<CFG.length;ci++)
    if (z>=CFG[ci].zMin&&z<=CFG[ci].zMax) {cfg=CFG[ci];break;}
  
  // 路线线段 → 像素
  var segPx = [];
  for (var i=0;i<routeSegData.length;i++) {
    var p1 = map.latLngToLayerPoint(L.latLng(routeSegData[i][0][0],routeSegData[i][0][1]));
    var p2 = map.latLngToLayerPoint(L.latLng(routeSegData[i][1][0],routeSegData[i][1][1]));
    segPx.push({x1:p1.x,y1:p1.y,x2:p2.x,y2:p2.y});
  }
  // 圆点 → 像素
  var dp = [];
  for (var i=0;i<cityPosData.length;i++) {
    var p = map.latLngToLayerPoint(L.latLng(cityPosData[i].lat,cityPosData[i].lng));
    dp.push(p);
  }
  
  labelLayer.clearLayers();
  leadLayer.clearLayers();
  
  var boxes = [];
  for (var i=0;i<cityPosData.length;i++) {
    var c = cityPosData[i];
    var cw = mw(c.name,14)+12;
    var p = findPos(c.lat,c.lng,cfg.basePx,cw,20,segPx,dp,boxes,true);
    boxes.push(p.box);
    labelLayer.addLayer(mkCity(p.lat,p.lng,c.color,c.name));
    if (cfg.lead) leadLayer.addLayer(mkLead(c.lat,c.lng,p.lat,p.lng,c.color));
  }
  
  for (var i=0;i<dxData.length;i++) {
    var d = dxData[i];
    if (cfg.compact) {
      var p = findPos(d.lat,d.lng,cfg.basePx*0.7,40,16,segPx,dp,boxes,true);
      boxes.push(p.box);
      labelLayer.addLayer(mkDxC(p.lat,p.lng,d.color,d.name));
    } else {
      var p = findPos(d.lat,d.lng,cfg.basePx*0.7,80,36,segPx,dp,boxes,false);
      boxes.push(p.box);
      labelLayer.addLayer(mkDx(p.lat,p.lng,d.color,d.name,d.sub||'',d.dist||''));
    }
  }
  
  // POI
  spurLayer.clearLayers();
  if (z>=10) {
    for (var i=0;i<spurRoutes.length;i++)
      spurLayer.addLayer(L.polyline(spurRoutes[i][1],{color:spurRoutes[i][0],weight:3,opacity:0.6,smoothFactor:1}));
  }
  if (z>=10&&!map.hasLayer(poiMajor)) map.addLayer(poiMajor);
  else if (z<10&&map.hasLayer(poiMajor)) map.removeLayer(poiMajor);
  if (z>=11&&!map.hasLayer(poiMinor)) map.addLayer(poiMinor);
  else if (z<11&&map.hasLayer(poiMinor)) map.removeLayer(poiMinor);
  if (!map.hasLayer(spurLayer)) map.addLayer(spurLayer);
  
  if (map.hasLayer(dotLayer)){map.removeLayer(dotLayer);map.addLayer(dotLayer);}
  if (map.hasLayer(labelLayer)){map.removeLayer(labelLayer);map.addLayer(labelLayer);}
}
map.on('zoomend',u); u();
