/**
 * Maps Planner: Leaflet + OpenStreetMap. Two markers: Input location + Nearby point (20 km).
 */
(function() {
  const API = '/api';
  const DEFAULT_CO = { lat: 17.3850, lng: 78.4867 };

  let mapInstance = null;
  let nearMarker = null;
  let inputMarker = null;

  function formatMoney(amount, currency, symbol) {
    if (amount == null || isNaN(amount)) return (symbol || '$') + '0';
    const num = Number(amount);
    const sym = symbol || '$';
    const locale = (currency || '').toUpperCase() === 'INR' ? 'en-IN' : 'en-US';
    const formatted = num.toLocaleString(locale, { maximumFractionDigits: 0, minimumFractionDigits: 0 });
    if (sym === '₹') return '₹' + formatted;
    if (sym === '£' || sym === '€') return sym + formatted;
    return '$' + formatted;
  }

  function fixLeafletDefaultIcons() {
    if (typeof L === 'undefined' || !L.Icon || !L.Icon.Default) return;
    try {
      delete L.Icon.Default.prototype._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
      });
    } catch (e) { /* ignore */ }
  }

  function initMap() {
    if (typeof L === 'undefined') return;
    const el = document.getElementById('map-container');
    if (!el || mapInstance) return;
    try {
      fixLeafletDefaultIcons();
      mapInstance = L.map('map-container').setView([DEFAULT_CO.lat, DEFAULT_CO.lng], 6);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(mapInstance);
      nearMarker = L.marker([DEFAULT_CO.lat, DEFAULT_CO.lng]).addTo(mapInstance).bindPopup('Nearby point (20 km)');
    } catch (err) {
      console.error('Map init failed', err);
    }
  }

  function scheduleMapResize() {
    [50, 200, 600].forEach(function(ms) {
      setTimeout(function() { window.mapsInvalidateSize && window.mapsInvalidateSize(); }, ms);
    });
  }

  /** Destination point (lat, lng) km away at bearing (degrees from north). */
  function destinationPointKm(lat, lng, distanceKm, bearingDeg) {
    var R = 6371;
    var brng = bearingDeg * Math.PI / 180;
    var d = distanceKm / R;
    var lat1 = lat * Math.PI / 180;
    var lon1 = lng * Math.PI / 180;
    var lat2 = Math.asin(Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(brng));
    var lon2 = lon1 + Math.atan2(Math.sin(brng) * Math.sin(d) * Math.cos(lat1), Math.cos(d) - Math.sin(lat1) * Math.sin(lat2));
    return [lat2 * 180 / Math.PI, ((lon2 * 180 / Math.PI + 540) % 360) - 180];
  }

  async function clientGeocodePhoton(query) {
    if (!query || query.trim().toLowerCase() === 'area') return null;
    try {
      var url = 'https://photon.komoot.io/api/?q=' + encodeURIComponent(query.trim()) + '&limit=1';
      var r = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!r.ok) return null;
      var data = await r.json();
      var feats = data.features || [];
      if (!feats.length) return null;
      var c = feats[0].geometry && feats[0].geometry.coordinates;
      if (!c || c.length < 2) return null;
      return { lat: c[1], lng: c[0] };
    } catch (e) {
      return null;
    }
  }

  function updateMapMarkers(inputLat, inputLng, nearLat, nearLng) {
    if (typeof L === 'undefined' || !mapInstance) return;
    try {
      if (inputMarker) mapInstance.removeLayer(inputMarker);
      if (nearMarker) mapInstance.removeLayer(nearMarker);

      const hasInput = inputLat != null && inputLng != null && !isNaN(inputLat) && !isNaN(inputLng);
      const hasNear = nearLat != null && nearLng != null && !isNaN(nearLat) && !isNaN(nearLng);

      if (hasInput) {
        inputMarker = L.marker([inputLat, inputLng]).addTo(mapInstance).bindPopup('Input Location');
      }
      if (hasNear) {
        nearMarker = L.marker([nearLat, nearLng]).addTo(mapInstance).bindPopup('Nearby point (20 km)');
      }
      if (hasInput && hasNear) {
        const group = L.featureGroup([inputMarker, nearMarker]);
        mapInstance.fitBounds(group.getBounds().pad(0.2));
      } else if (hasInput) {
        mapInstance.setView([inputLat, inputLng], 11);
      } else {
        mapInstance.setView([DEFAULT_CO.lat, DEFAULT_CO.lng], 6);
      }
    } catch (err) {
      console.error('Update markers failed', err);
    }
    scheduleMapResize();
  }

  function renderMapsResult(data, searchQuery) {
    const d = data || {};
    const sym = d.currency_symbol || '₹';
    const curr = d.currency || 'INR';

    var areaEl = document.getElementById('maps-area-type');
    var distEl = document.getElementById('maps-distance');
    var archEl = document.getElementById('maps-architecture');
    var costEl = document.getElementById('maps-total-cost');
    if (areaEl) areaEl.textContent = d.inferred_location_type || d.area_type || '—';
    if (distEl) distEl.textContent = (d.distance_display_km != null ? d.distance_display_km + ' km' : d.inferred_distance_km != null ? d.inferred_distance_km + ' km' : '—');
    if (archEl) archEl.textContent = d.inferred_architecture || d.architecture_type || '—';
    if (costEl) costEl.textContent = formatMoney(d.total_cost, curr, sym);

    var breakdown = d.cost_breakdown_display || d.cost_breakdown || {};
    var list = document.getElementById('maps-breakdown');
    if (list) list.innerHTML = Object.keys(breakdown).length ? Object.entries(breakdown).map(function(entry) { return '<li><span>' + entry[0] + '</span><span>' + formatMoney(entry[1], curr, sym) + '</span></li>'; }).join('') : '<li>—</li>';

    var opts = d.optimization_suggestions || [];
    var optList = document.getElementById('maps-optimizations');
    if (optList) optList.innerHTML = opts.length ? opts.map(function(s) { return '<li>' + (typeof s === 'string' ? s : String(s)) + '</li>'; }).join('') : '<li>No suggestions</li>';

    var resPanel = document.getElementById('maps-result');
    var placePanel = document.getElementById('maps-placeholder');
    if (resPanel) resPanel.style.display = 'block';
    if (placePanel) placePanel.style.display = 'none';

    var ulat = d.user_lat != null ? Number(d.user_lat) : null;
    var ulng = d.user_lng != null ? Number(d.user_lng) : null;
    var nlat = d.co_lat != null ? Number(d.co_lat) : null;
    var nlng = d.co_lng != null ? Number(d.co_lng) : null;
    var hasUser = ulat != null && ulng != null && !isNaN(ulat) && !isNaN(ulng);

    function applyMarkers(lat, lng, nearLat, nearLng) {
      updateMapMarkers(lat, lng, nearLat, nearLng);
      var hint = document.getElementById('map-hint');
      if (hint) {
        if (lat != null && lng != null && !isNaN(lat) && !isNaN(lng)) {
          hint.textContent = 'Distance: 20 km between Input Location and Nearby point.';
        } else {
          hint.textContent = 'Location could not be geocoded. Try a fuller address (city, region, country).';
        }
      }
    }

    if (!hasUser && searchQuery && searchQuery.trim() && searchQuery.trim().toLowerCase() !== 'area') {
      clientGeocodePhoton(searchQuery).then(function(pt) {
        if (pt) {
          var dest = destinationPointKm(pt.lat, pt.lng, 20, 45);
          applyMarkers(pt.lat, pt.lng, dest[0], dest[1]);
        } else {
          applyMarkers(ulat, ulng, nlat, nlng);
        }
      });
    } else {
      applyMarkers(ulat, ulng, nlat, nlng);
    }

    var saveBtn = document.getElementById('btn-save-maps');
    if (saveBtn) saveBtn.onclick = function() { if (window.saveCurrentProject) window.saveCurrentProject(); };
  }

  function ensureMapReady() {
    if (mapInstance) return;
    initMap();
  }

  function initMapsPanel() {
    const btn = document.getElementById('btn-run-maps');
    if (!btn) return;

    document.querySelectorAll('.nav-item[data-panel="maps-planner"]').forEach(function(nav) {
      nav.addEventListener('click', function() {
        ensureMapReady();
        window.mapsInvalidateSize && window.mapsInvalidateSize();
      });
    });

    btn.addEventListener('click', async function() {
      ensureMapReady();
      var locationInput = document.getElementById('maps-location');
      var premisesInput = document.getElementById('maps-premises');
      const location = (locationInput && locationInput.value ? locationInput.value.trim() : '') || 'Area';
      const premisesRaw = premisesInput ? premisesInput.value : '';
      const premises = Math.max(1, Math.min(100000, parseInt(premisesRaw, 10) || 51));
      btn.disabled = true;
      var resPanel = document.getElementById('maps-result');
      var placePanel = document.getElementById('maps-placeholder');
      if (resPanel) resPanel.style.display = 'none';
      if (placePanel) { placePanel.style.display = 'block'; placePanel.textContent = 'Loading...'; }
      try {
        function numOrNull(v) {
          if (v == null) return null;
          const n = Number(v);
          return Number.isFinite(n) ? n : null;
        }
        function readCostParams(prefix) {
          const p = prefix || 'maps-cp-';
          const keys = [
            'fiber_per_km',
            'splitter_1_32',
            'splitter_1_64',
            'olt_port',
            'ont_unit',
            'cabinet',
            'civil_per_km',
            'labor_per_premise',
            'maintenance_year_pct'
          ];
          const out = {};
          keys.forEach(function(k) {
            var el = document.getElementById(p + k);
            if (!el) return;
            var n = numOrNull(el.value);
            if (n == null || n < 0) return;
            out[k] = n;
          });
          return out;
        }
        var costParams = readCostParams('maps-cp-');
        const res = await fetch(API + '/maps/estimate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(Object.assign({ target_location: location, total_premises: premises }, costParams))
        });
        const data = await res.json().catch(function() { return {}; });
        if (!res.ok) {
          var msg = data.detail;
          if (Array.isArray(msg)) msg = (msg[0] && msg[0].msg) ? msg[0].msg : msg.map(function(m) { return m.msg || m; }).join('. ');
          else if (msg && typeof msg !== 'string') msg = String(msg);
          throw new Error(msg || 'Request failed');
        }
        window.lastEstimationResult = data;
        window.lastEstimationType = 'maps_planner';
        window.lastEstimationInputs = Object.assign({ target_location: location, total_premises: premises }, costParams);
        renderMapsResult(data, location);
      } catch (e) {
        var errMsg = (e && e.message) ? e.message : (typeof e === 'string' ? e : 'Request failed');
        var ph = document.getElementById('maps-placeholder');
        if (ph) { ph.textContent = 'Error: ' + errMsg; ph.style.display = 'block'; }
      }
      btn.disabled = false;
    });
  }

  document.addEventListener('DOMContentLoaded', initMapsPanel);

  window.mapsInvalidateSize = function() {
    setTimeout(function() {
      if (mapInstance && typeof mapInstance.invalidateSize === 'function') mapInstance.invalidateSize();
    }, 200);
  };
})();
