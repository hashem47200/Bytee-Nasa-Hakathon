/* Bytee 3D Planetary Exploration Engine & Telemetry HUD */
(function () {
  'use strict';

  const container = document.getElementById('planet-canvas-container');
  if (!container || typeof THREE === 'undefined') return;

  const planetData = window.PLANET_VIEWER_DATA || {};
  let currentPlanet = 'mars'; // default planet

  // UI Elements
  const toggleMarsBtn = document.getElementById('btn-planet-mars');
  const toggleMoonBtn = document.getElementById('btn-planet-moon');
  const spinToggleBtn = document.getElementById('btn-spin-toggle');
  const spinIcon = document.getElementById('spin-icon');
  const spinText = document.getElementById('spin-text');
  const zoomInBtn = document.getElementById('btn-zoom-in');
  const zoomOutBtn = document.getElementById('btn-zoom-out');
  const resetViewBtn = document.getElementById('btn-reset-view');

  const sidebarList = document.getElementById('planet-sidebar-missions');
  const sidebarTitle = document.getElementById('planet-sidebar-title');
  const sidebarDesc = document.getElementById('planet-view-desc');
  const vehicleCountBadge = document.getElementById('planet-vehicle-count');
  const tooltip = document.getElementById('planet-tooltip');

  // Modal Elements
  const modal = document.getElementById('vehicle-modal');
  const modalCloseBtn = document.getElementById('modal-close');
  const modalImg = document.getElementById('modal-vehicle-img');
  const modalType = document.getElementById('modal-vehicle-type');
  const modalCode = document.getElementById('modal-vehicle-code');
  const modalName = document.getElementById('modal-vehicle-name');
  const modalTagline = document.getElementById('modal-vehicle-tagline');
  const modalLaunch = document.getElementById('modal-launch-date');
  const modalLanding = document.getElementById('modal-landing-date');
  const modalCoords = document.getElementById('modal-coordinates');
  const modalStory = document.getElementById('modal-vehicle-story');
  const modalExamBtn = document.getElementById('modal-exam-btn');
  const modalDossierBtn = document.getElementById('modal-dossier-btn');

  // State
  let autoRotate = true;
  let isDragging = false;
  let prevPointerPos = { x: 0, y: 0 };
  let targetRotationX = 0;
  let targetRotationY = 0;
  const DEFAULT_CAM_Z = 2.7;

  // Scene setup
  const scene = new THREE.Scene();
  const width = container.clientWidth || 600;
  const height = container.clientHeight || 520;

  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, 0, DEFAULT_CAM_Z);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  container.appendChild(renderer.domElement);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
  scene.add(ambientLight);

  const sunLight = new THREE.DirectionalLight(0xffffff, 0.9);
  sunLight.position.set(5, 3, 5);
  scene.add(sunLight);

  // Planet Sphere Mesh
  const sphereGeo = new THREE.SphereGeometry(1, 64, 64);
  const textureLoader = new THREE.TextureLoader();

  const planetMat = new THREE.MeshStandardMaterial({
    roughness: 0.85,
    metalness: 0.1,
  });

  const planetMesh = new THREE.Mesh(sphereGeo, planetMat);
  scene.add(planetMesh);

  // Atmosphere glow ring
  const glowGeo = new THREE.SphereGeometry(1.025, 32, 32);
  const glowMat = new THREE.MeshBasicMaterial({
    color: 0xff5533,
    transparent: true,
    opacity: 0.16,
    side: THREE.BackSide,
  });
  const glowMesh = new THREE.Mesh(glowGeo, glowMat);
  scene.add(glowMesh);

  // Groups
  const markersGroup = new THREE.Group();
  planetMesh.add(markersGroup);

  const orbitalGroup = new THREE.Group();
  scene.add(orbitalGroup);

  // Raycasting
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();
  let interactiveMeshes = [];

  // Helper: Lat/Lon to 3D Vector
  function latLonToVector3(lat, lon, radius) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = (radius * Math.sin(phi) * Math.sin(theta));
    const y = (radius * Math.cos(phi));
    return new THREE.Vector3(x, y, z);
  }

  // Load Celestial Body (Mars or Moon)
  function loadPlanet(slug) {
    currentPlanet = slug;
    const info = planetData[slug];
    if (!info) return;

    if (sidebarTitle) {
      sidebarTitle.textContent = slug === 'mars' ? 'Martian Vehicles & Telemetry' : 'Lunar Surface Vehicles';
    }
    if (sidebarDesc && info.description) {
      sidebarDesc.textContent = info.description;
    }

    // Toggle button UI state
    if (toggleMarsBtn) toggleMarsBtn.classList.toggle('is-active', slug === 'mars');
    if (toggleMoonBtn) toggleMoonBtn.classList.toggle('is-active', slug === 'moon');

    // Texture update
    if (info.texture) {
      textureLoader.load(info.texture, function (tex) {
        planetMat.map = tex;
        planetMat.needsUpdate = true;
      });
    }

    // Glow effect update
    if (slug === 'mars') {
      glowMat.color.setHex(0xff5533);
      glowMat.opacity = 0.18;
    } else {
      glowMat.color.setHex(0x38e1ff);
      glowMat.opacity = 0.12;
    }

    // Clear old markers
    while (markersGroup.children.length > 0) {
      markersGroup.remove(markersGroup.children[0]);
    }
    while (orbitalGroup.children.length > 0) {
      orbitalGroup.remove(orbitalGroup.children[0]);
    }
    interactiveMeshes = [];

    // Clear sidebar list
    if (sidebarList) sidebarList.innerHTML = '';

    const vehicles = info.vehicles || [];
    if (vehicleCountBadge) {
      vehicleCountBadge.textContent = vehicles.length + ' Beacons';
    }

    vehicles.forEach(function (v, idx) {
      const isNearbySpace = Boolean(v.is_nearby_space);

      if (isNearbySpace) {
        // --- 1. NEARBY-SPACE / ORBITAL VEHICLE (Floating beacon around Mars) ---
        const orbitRadius = v.orbit_altitude || (1.45 + (idx % 4) * 0.12);
        const orbitAngle = ((idx * 85) + 30) * (Math.PI / 180);
        const orbitY = ((idx % 3) - 1) * 0.35;

        // Visual orbit guide ring
        const orbitCurveGeo = new THREE.RingGeometry(orbitRadius - 0.005, orbitRadius + 0.005, 64);
        const orbitCurveMat = new THREE.MeshBasicMaterial({
          color: 0x8a63d2,
          transparent: true,
          opacity: 0.35,
          side: THREE.DoubleSide
        });
        const orbitCurveMesh = new THREE.Mesh(orbitCurveGeo, orbitCurveMat);
        orbitCurveMesh.rotation.x = Math.PI / 2 + (idx * 0.15);
        orbitalGroup.add(orbitCurveMesh);

        // Floating Probe Marker
        const probeGeo = new THREE.OctahedronGeometry(0.045, 0);
        const probeMat = new THREE.MeshBasicMaterial({ color: 0xc490ff });
        const probeMesh = new THREE.Mesh(probeGeo, probeMat);

        const x = Math.cos(orbitAngle) * orbitRadius;
        const z = Math.sin(orbitAngle) * orbitRadius;
        probeMesh.position.set(x, orbitY, z);
        probeMesh.userData = v;

        // Glowing beacon halo
        const haloGeo = new THREE.RingGeometry(0.055, 0.075, 24);
        const haloMat = new THREE.MeshBasicMaterial({
          color: 0x9d5cff,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.85
        });
        const haloMesh = new THREE.Mesh(haloGeo, haloMat);
        haloMesh.position.copy(probeMesh.position);
        haloMesh.lookAt(new THREE.Vector3(0, 0, 0));

        orbitalGroup.add(probeMesh);
        orbitalGroup.add(haloMesh);
        interactiveMeshes.push(probeMesh);

      } else {
        // --- 2. SURFACE VEHICLE (Anchored directly on planetary surface) ---
        const pos = latLonToVector3(v.lat, v.lon, 1.018);

        const pinGeo = new THREE.SphereGeometry(0.032, 16, 16);
        const pinColor = slug === 'mars' ? 0xffc94d : 0x3dff9a;
        const pinMat = new THREE.MeshBasicMaterial({ color: pinColor });
        const pinMesh = new THREE.Mesh(pinGeo, pinMat);
        pinMesh.position.copy(pos);
        pinMesh.userData = v;

        // Locator pulse ring
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
        interactiveMeshes.push(pinMesh);
      }

      // Sidebar Mission Item
      if (sidebarList) {
        const item = document.createElement('div');
        item.className = 'planet-sidebar-item';
        item.dataset.slug = v.slug;
        const typeBadge = isNearbySpace ? '<span class="item-type-tag tag--orbit">ORBIT</span>' : '<span class="item-type-tag tag--surf">SURFACE</span>';

        item.innerHTML =
          '<div class="item-head">' +
            '<span class="item-dot ' + (isNearbySpace ? 'dot--orbit' : 'dot--surf') + '"></span>' +
            '<strong>' + v.name + '</strong>' +
            typeBadge +
          '</div>' +
          '<div class="item-meta">' +
            (v.date ? '<span>📅 ' + v.date + '</span>' : '') +
            (v.coords ? '<span>📍 ' + v.coords + '</span>' : '') +
          '</div>' +
          '<div class="item-actions">' +
            '<button type="button" class="btn btn--xs btn-inspect">Inspect 🔍</button>' +
            '<a href="' + v.quiz_url + '" class="btn btn--xs btn--primary">Exam 🚀</a>' +
          '</div>';

        // Hover focuses coordinate
        item.addEventListener('mouseenter', function () {
          if (!isNearbySpace) {
            focusOnCoordinates(v.lat, v.lon);
          }
          highlightSidebarItem(v.slug);
        });

        // Click opens modal
        item.addEventListener('click', function (e) {
          if (e.target.tagName.toLowerCase() === 'a') return; // let exam link follow
          openVehicleModal(v);
        });

        sidebarList.appendChild(item);
      }
    });
  }

  // Focus Coordinates
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

  // Open In-Scene Vehicle Information Window (Modal)
  function openVehicleModal(v) {
    if (!modal) return;

    if (modalImg) {
      modalImg.src = v.image || '/static/images/placeholder.svg';
      modalImg.alt = v.name;
    }
    if (modalType) {
      modalType.textContent = v.is_nearby_space ? 'NEARBY-SPACE ORBITAL PROBE' : 'SURFACE VEHICLE & LANDER';
      modalType.className = 'modal-type-badge ' + (v.is_nearby_space ? 'badge--orbit' : 'badge--surface');
    }
    if (modalCode) modalCode.textContent = v.code || 'BYTEE-MISSION';
    if (modalName) modalName.textContent = v.name;
    if (modalTagline) modalTagline.textContent = v.tagline || '';
    if (modalLaunch) modalLaunch.textContent = v.launch_date || 'N/A';
    if (modalLanding) modalLanding.textContent = v.landing_date || 'N/A';
    if (modalCoords) modalCoords.textContent = v.raw_location || v.coords || 'Martian System';
    if (modalStory) modalStory.textContent = v.story || v.notes || 'Authentic mission telemetry recorded by Bytee mission operations.';

    if (modalExamBtn) modalExamBtn.href = v.quiz_url;
    if (modalDossierBtn) modalDossierBtn.href = v.url;

    modal.style.display = 'flex';
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeVehicleModal() {
    if (!modal) return;
    modal.style.display = 'none';
    modal.setAttribute('aria-hidden', 'true');
  }

  if (modalCloseBtn) {
    modalCloseBtn.addEventListener('click', closeVehicleModal);
  }
  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) closeVehicleModal();
    });
  }
  window.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && modal && modal.style.display === 'flex') {
      closeVehicleModal();
    }
  });

  // Switch buttons
  if (toggleMarsBtn) {
    toggleMarsBtn.addEventListener('click', function () {
      loadPlanet('mars');
    });
  }
  if (toggleMoonBtn) {
    toggleMoonBtn.addEventListener('click', function () {
      loadPlanet('moon');
    });
  }

  // Spin toggle
  if (spinToggleBtn) {
    spinToggleBtn.addEventListener('click', function () {
      autoRotate = !autoRotate;
      if (spinIcon) spinIcon.textContent = autoRotate ? '⏸' : '▶';
      if (spinText) spinText.textContent = autoRotate ? 'Pause' : 'Resume';
      spinToggleBtn.classList.toggle('is-paused', !autoRotate);
    });
  }

  // Zoom controls
  function setZoom(delta) {
    camera.position.z += delta;
    camera.position.z = Math.max(1.5, Math.min(4.8, camera.position.z));
  }

  if (zoomInBtn) {
    zoomInBtn.addEventListener('click', function () {
      setZoom(-0.35);
    });
  }
  if (zoomOutBtn) {
    zoomOutBtn.addEventListener('click', function () {
      setZoom(0.35);
    });
  }

  // Reset view
  if (resetViewBtn) {
    resetViewBtn.addEventListener('click', function () {
      camera.position.set(0, 0, DEFAULT_CAM_Z);
      targetRotationX = 0;
      targetRotationY = 0;
      planetMesh.rotation.set(0, 0, 0);
      orbitalGroup.rotation.set(0, 0, 0);
    });
  }

  // Mouse / Touch Drag Controls
  container.addEventListener('mousedown', function (e) {
    isDragging = true;
    prevPointerPos = { x: e.clientX, y: e.clientY };
    container.style.cursor = 'grabbing';
  });

  window.addEventListener('mouseup', function () {
    isDragging = false;
    if (container) container.style.cursor = 'grab';
  });

  container.addEventListener('mousemove', function (e) {
    if (isDragging) {
      const deltaX = e.clientX - prevPointerPos.x;
      const deltaY = e.clientY - prevPointerPos.y;

      planetMesh.rotation.y += deltaX * 0.005;
      planetMesh.rotation.x += deltaY * 0.005;
      orbitalGroup.rotation.y += deltaX * 0.003;

      targetRotationY = planetMesh.rotation.y;
      targetRotationX = planetMesh.rotation.x;

      prevPointerPos = { x: e.clientX, y: e.clientY };
    }
  });

  // Wheel Zoom
  container.addEventListener('wheel', function (e) {
    e.preventDefault();
    setZoom(e.deltaY * 0.002);
  }, { passive: false });

  // Touch Support (Drag & Pinch to Zoom)
  let touchStartDist = 0;
  container.addEventListener('touchstart', function (e) {
    if (e.touches.length === 1) {
      isDragging = true;
      prevPointerPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    } else if (e.touches.length === 2) {
      isDragging = false;
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      touchStartDist = Math.hypot(dx, dy);
    }
  }, { passive: true });

  container.addEventListener('touchmove', function (e) {
    if (e.touches.length === 1 && isDragging) {
      const deltaX = e.touches[0].clientX - prevPointerPos.x;
      const deltaY = e.touches[0].clientY - prevPointerPos.y;

      planetMesh.rotation.y += deltaX * 0.006;
      planetMesh.rotation.x += deltaY * 0.006;
      orbitalGroup.rotation.y += deltaX * 0.004;

      prevPointerPos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const currentDist = Math.hypot(dx, dy);
      if (touchStartDist > 0) {
        const pinchDelta = (touchStartDist - currentDist) * 0.005;
        setZoom(pinchDelta);
        touchStartDist = currentDist;
      }
    }
  }, { passive: true });

  container.addEventListener('touchend', function () {
    isDragging = false;
    touchStartDist = 0;
  });

  // Raycasting for Tooltip and Click
  container.addEventListener('mousemove', function (e) {
    if (isDragging) return;

    const rect = container.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / container.clientWidth) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / container.clientHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(interactiveMeshes);

    if (intersects.length > 0) {
      const v = intersects[0].object.userData;
      if (v) {
        container.style.cursor = 'pointer';
        if (tooltip) {
          tooltip.style.display = 'block';
          tooltip.style.left = (e.clientX - rect.left + 14) + 'px';
          tooltip.style.top = (e.clientY - rect.top + 14) + 'px';
          tooltip.innerHTML =
            '<div class="tip-head"><strong>' + v.name + '</strong></div>' +
            '<div class="tip-meta">' +
              (v.date ? '<span>📅 ' + v.date + '</span>' : '') +
              (v.coords ? '<span>📍 ' + v.coords + '</span>' : '') +
            '</div>' +
            '<div class="tip-cta">Click beacon to inspect mission</div>';
        }
        highlightSidebarItem(v.slug);
      }
    } else {
      container.style.cursor = 'grab';
      if (tooltip) tooltip.style.display = 'none';
    }
  });

  // Click Marker -> Opens In-Scene Modal
  container.addEventListener('click', function (e) {
    if (isDragging) return;
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(interactiveMeshes);
    if (intersects.length > 0) {
      const v = intersects[0].object.userData;
      if (v) {
        openVehicleModal(v);
      }
    }
  });

  // Window Resize
  window.addEventListener('resize', function () {
    const w = container.clientWidth || 600;
    const h = container.clientHeight || 520;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });

  // Animation Loop
  function animate() {
    requestAnimationFrame(animate);

    if (!isDragging) {
      if (Math.abs(targetRotationY - planetMesh.rotation.y) > 0.01) {
        planetMesh.rotation.y += (targetRotationY - planetMesh.rotation.y) * 0.05;
        planetMesh.rotation.x += (targetRotationX - planetMesh.rotation.x) * 0.05;
      } else if (autoRotate) {
        planetMesh.rotation.y += 0.0018; // smooth idle spin
        orbitalGroup.rotation.y += 0.0012; // slow orbital drift
      }
    }

    renderer.render(scene, camera);
  }

  // Initial load
  loadPlanet('mars');
  animate();

})();
