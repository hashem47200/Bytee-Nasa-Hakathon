/* 3D Planet Interactive Viewer, Sidebar Toggle and Mission Markers */
(function () {
  'use strict';

  const container = document.getElementById('planet-canvas-container');
  const toggleButtons = Array.from(document.querySelectorAll('[data-planet-toggle]'));
  const sidebarList = document.getElementById('planet-sidebar-missions');
  const sidebarTitle = document.getElementById('planet-sidebar-title');
  const vehicleCountBadge = document.getElementById('planet-vehicle-count');
  const tooltip = document.getElementById('planet-tooltip');

  if (!container || typeof THREE === 'undefined') return;

  const planetData = window.PLANET_VIEWER_DATA || {};
  let currentPlanet = 'mars'; // default planet

  // Scene setup
  const scene = new THREE.Scene();
  const width = container.clientWidth || 600;
  const height = container.clientHeight || 480;

  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.z = 2.6;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.appendChild(renderer.domElement);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 0.85);
  dirLight.position.set(5, 3, 5);
  scene.add(dirLight);

  // Planet Sphere Mesh
  const sphereGeo = new THREE.SphereGeometry(1, 64, 64);
  const textureLoader = new THREE.TextureLoader();

  const planetMat = new THREE.MeshStandardMaterial({
    roughness: 0.85,
    metalness: 0.1
  });

  const planetMesh = new THREE.Mesh(sphereGeo, planetMat);
  scene.add(planetMesh);

  // Atmosphere glow ring
  const glowGeo = new THREE.SphereGeometry(1.025, 32, 32);
  const glowMat = new THREE.MeshBasicMaterial({
    color: 0xff5533,
    transparent: true,
    opacity: 0.15,
    side: THREE.BackSide
  });
  const glowMesh = new THREE.Mesh(glowGeo, glowMat);
  scene.add(glowMesh);

  // Group for vehicle markers on surface
  const markersGroup = new THREE.Group();
  planetMesh.add(markersGroup);

  // Helper: Convert Lat/Lon to 3D Cartesian on unit sphere
  function latLonToVector3(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = (radius * Math.sin(phi) * Math.sin(theta));
    const y = (radius * Math.cos(phi));
    return new THREE.Vector3(x, y, z);
  }

  // Marker meshes cache for raycasting
  let markerMeshes = [];

  function loadPlanet(slug) {
    currentPlanet = slug;
    const info = planetData[slug];
    if (!info) return;

    if (sidebarTitle) {
      if (slug === 'mars') sidebarTitle.textContent = 'Mars Surface Vehicles';
      else if (slug === 'moon') sidebarTitle.textContent = 'Lunar Surface Vehicles';
      else sidebarTitle.textContent = 'Deep Space Vehicles';
    }

    const planetTitle = document.getElementById('planet-view-title');
    const planetDesc = document.getElementById('planet-view-desc');
    if (planetTitle && info.name) {
      planetTitle.innerHTML = '<span class="pulse-dot"></span> ' + info.name + ' Telemetry';
    }
    if (planetDesc && info.description) {
      planetDesc.textContent = info.description;
    }

    // Update texture
    if (info.texture) {
      textureLoader.load(info.texture, function (tex) {
        planetMat.map = tex;
        planetMat.needsUpdate = true;
      });
    }

    // Update glow color
    if (slug === 'mars') {
      glowMat.color.setHex(0xff5533);
      glowMat.opacity = 0.16;
    } else if (slug === 'moon') {
      glowMat.color.setHex(0x38e1ff);
      glowMat.opacity = 0.12;
    } else {
      glowMat.color.setHex(0xb9a2ff);
      glowMat.opacity = 0.22;
    }

    // Rebuild vehicle surface markers
    while (markersGroup.children.length > 0) {
      markersGroup.remove(markersGroup.children[0]);
    }
    markerMeshes = [];

    // Rebuild sidebar list
    if (sidebarList) sidebarList.innerHTML = '';

    const vehicles = info.vehicles || [];
    if (vehicleCountBadge) {
      vehicleCountBadge.textContent = vehicles.length + ' Beacons';
    }

    vehicles.forEach(function (v) {
      // 1. Add 3D Marker Pin
      const pos = latLonToVector3(v.lat, v.lon, 1.018);

      // Marker anchor
      const pinGeo = new THREE.SphereGeometry(0.032, 16, 16);
      const pinColor = slug === 'mars' ? 0xffc94d : (slug === 'moon' ? 0x3dff9a : 0x38e1ff);
      const pinMat = new THREE.MeshBasicMaterial({ color: pinColor });
      const pinMesh = new THREE.Mesh(pinGeo, pinMat);
      pinMesh.position.copy(pos);
      pinMesh.userData = v;

      // Pulse ring around pin
      const ringGeo = new THREE.RingGeometry(0.042, 0.058, 24);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.8
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.copy(pos.clone().multiplyScalar(1.002));
      ringMesh.lookAt(pos.clone().multiplyScalar(2));

      markersGroup.add(pinMesh);
      markersGroup.add(ringMesh);
      markerMeshes.push(pinMesh);

      // 2. Add Sidebar interactive item
      if (sidebarList) {
        const item = document.createElement('div');
        item.className = 'planet-sidebar-item';
        item.dataset.slug = v.slug;
        item.innerHTML =
          '<div class="item-head">' +
            '<span class="item-dot"></span>' +
            '<strong>' + v.name + '</strong>' +
          '</div>' +
          '<div class="item-meta">' +
            (v.date ? '<span>📅 ' + v.date + '</span>' : '') +
            (v.coords ? '<span>📍 ' + v.coords + '</span>' : '') +
          '</div>' +
          '<div class="item-actions">' +
            '<a href="' + v.url + '" class="btn btn--xs">Dossier 📖</a>' +
            '<a href="' + v.quiz_url + '" class="btn btn--xs btn--primary">Exam 🚀</a>' +
          '</div>';

        // Hovering sidebar item rotates planet to focus on vehicle
        item.addEventListener('mouseenter', function () {
          focusOnCoordinates(v.lat, v.lon);
          highlightSidebarItem(v.slug);
        });

        sidebarList.appendChild(item);
      }
    });

    // Update active state on toggle buttons
    toggleButtons.forEach(function (btn) {
      const active = btn.dataset.planetToggle === slug;
      btn.classList.toggle('active', active);
      btn.classList.toggle('is-active', active);
    });
  }

  // Smoothly rotate sphere to center a specific lat/lon in front of camera
  let targetRotationX = 0;
  let targetRotationY = 0;

  function focusOnCoordinates(lat, lon) {
    const phi = (lat) * (Math.PI / 180);
    const theta = (-lon - 90) * (Math.PI / 180);
    targetRotationX = phi * 0.7;
    targetRotationY = theta;
  }

  function highlightSidebarItem(slug) {
    if (!sidebarList) return;
    const items = sidebarList.querySelectorAll('.planet-sidebar-item');
    items.forEach(function (el) {
      if (el.dataset.slug === slug) {
        el.classList.add('is-active');
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      } else {
        el.classList.remove('is-active');
      }
    });
  }

  // Toggle buttons click listener
  toggleButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      loadPlanet(btn.dataset.planetToggle);
    });
  });

  // User Orbit & Drag Controls
  let isDragging = false;
  let prevMousePos = { x: 0, y: 0 };

  container.addEventListener('mousedown', function (e) {
    isDragging = true;
    prevMousePos = { x: e.clientX, y: e.clientY };
    container.style.cursor = 'grabbing';
  });

  window.addEventListener('mouseup', function () {
    isDragging = false;
    if (container) container.style.cursor = 'grab';
  });

  container.addEventListener('mousemove', function (e) {
    if (isDragging) {
      const deltaX = e.clientX - prevMousePos.x;
      const deltaY = e.clientY - prevMousePos.y;

      planetMesh.rotation.y += deltaX * 0.005;
      planetMesh.rotation.x += deltaY * 0.005;
      targetRotationY = planetMesh.rotation.y;
      targetRotationX = planetMesh.rotation.x;

      prevMousePos = { x: e.clientX, y: e.clientY };
    }
  });

  // Zoom with scroll wheel
  container.addEventListener('wheel', function (e) {
    e.preventDefault();
    camera.position.z += e.deltaY * 0.002;
    camera.position.z = Math.max(1.6, Math.min(4.5, camera.position.z));
  }, { passive: false });

  // Raycasting for marker hover and tooltip
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  container.addEventListener('mousemove', function (e) {
    if (isDragging) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / container.clientWidth) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / container.clientHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(markerMeshes);

    if (intersects.length > 0) {
      const v = intersects[0].object.userData;
      if (v) {
        container.style.cursor = 'pointer';
        if (tooltip) {
          tooltip.style.display = 'block';
          tooltip.style.left = (e.clientX - rect.left + 14) + 'px';
          tooltip.style.top = (e.clientY - rect.top + 14) + 'px';
          tooltip.innerHTML =
            '<strong>' + v.name + '</strong>' +
            '<div class="tooltip-meta">' +
              (v.date ? '<span>📅 ' + v.date + '</span>' : '') +
              (v.coords ? '<span>📍 ' + v.coords + '</span>' : '') +
            '</div>' +
            '<div class="tooltip-tip">Click to view mission dossier</div>';
        }
        highlightSidebarItem(v.slug);
      }
    } else {
      container.style.cursor = 'grab';
      if (tooltip) tooltip.style.display = 'none';
    }
  });

  // Clicking a 3D marker navigates to the vehicle detail page
  container.addEventListener('click', function (e) {
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(markerMeshes);
    if (intersects.length > 0) {
      const v = intersects[0].object.userData;
      if (v && v.url) {
        window.location.href = v.url;
      }
    }
  });

  // Window resize handler
  window.addEventListener('resize', function () {
    const w = container.clientWidth || 600;
    const h = container.clientHeight || 480;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  // Animation loop with gentle idle rotation
  function animate() {
    requestAnimationFrame(animate);

    if (!isDragging) {
      if (Math.abs(targetRotationY - planetMesh.rotation.y) > 0.01) {
        planetMesh.rotation.y += (targetRotationY - planetMesh.rotation.y) * 0.05;
        planetMesh.rotation.x += (targetRotationX - planetMesh.rotation.x) * 0.05;
      } else {
        planetMesh.rotation.y += 0.0018; // idle spin
      }
    }

    renderer.render(scene, camera);
  }

  // Initial load
  loadPlanet('mars');
  animate();

})();
