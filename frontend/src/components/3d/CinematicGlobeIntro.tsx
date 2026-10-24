import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Eye, ArrowRight, Compass, ShieldAlert, Sparkles, Navigation } from 'lucide-react';

interface CinematicGlobeIntroProps {
  onComplete: () => void;
}

export const CinematicGlobeIntro: React.FC<CinematicGlobeIntroProps> = ({ onComplete }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<'approaching' | 'zoomed' | 'ready'>('approaching');
  const [targetName, setTargetName] = useState<string>('PLANETARY ORBIT');
  const [coordinatesText, setCoordinatesText] = useState<string>('28.3949° N, 84.1240° E');
  const [isExiting, setIsExiting] = useState<boolean>(false);
  const animFrameId = useRef<number | null>(null);
  const handleFinishRef = useRef<() => void>(() => {});

  const handleFinish = () => {
    if (isExiting) return;
    setIsExiting(true);
    setTimeout(() => {
      onComplete();
    }, 350);
  };
  handleFinishRef.current = handleFinish;

  useEffect(() => {
    if (!mountRef.current) return;

    const width = mountRef.current.clientWidth || window.innerWidth;
    const height = mountRef.current.clientHeight || window.innerHeight;

    // 1. Scene, Camera, Renderer
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x030712, 0.0015);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 5, 28);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch (e) {
      console.warn('WebGL initialization failed for Cinematic Intro, bypassing to Dashboard:', e);
      onComplete();
      return;
    }

    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mountRef.current.appendChild(renderer.domElement);

    // 2. Starfield & Cosmic Dust
    const starCount = 1800;
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    const starColors = new Float32Array(starCount * 3);

    for (let i = 0; i < starCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 180;
      starPositions[i + 1] = (Math.random() - 0.5) * 180;
      starPositions[i + 2] = (Math.random() - 0.5) * 180;

      // Deep cyan, ice blue, and soft white stars
      starColors[i] = 0.5 + Math.random() * 0.5;
      starColors[i + 1] = 0.8 + Math.random() * 0.2;
      starColors[i + 2] = 1.0;
    }

    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    starGeometry.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
    const starMaterial = new THREE.PointsMaterial({
      size: 0.6,
      vertexColors: true,
      transparent: true,
      opacity: 0.85
    });
    const starField = new THREE.Points(starGeometry, starMaterial);
    scene.add(starField);

    // 3. Central Earth Globe
    const globeRadius = 8.5;
    const globeGroup = new THREE.Group();
    scene.add(globeGroup);

    // Base dark sphere
    const globeGeo = new THREE.SphereGeometry(globeRadius, 64, 64);
    const globeMat = new THREE.MeshPhongMaterial({
      color: 0x071126,
      emissive: 0x020713,
      specular: 0x00f3ff,
      shininess: 25,
      wireframe: false
    });
    const globeMesh = new THREE.Mesh(globeGeo, globeMat);
    globeGroup.add(globeMesh);

    // Geospatial Grid Sphere
    const gridGeo = new THREE.SphereGeometry(globeRadius * 1.002, 36, 18);
    const gridMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      wireframe: true,
      transparent: true,
      opacity: 0.12
    });
    const gridMesh = new THREE.Mesh(gridGeo, gridMat);
    globeGroup.add(gridMesh);

    // Atmospheric Glow
    const atmosGeo = new THREE.SphereGeometry(globeRadius * 1.08, 64, 64);
    const atmosMat = new THREE.ShaderMaterial({
      vertexShader: `
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec3 vNormal;
        void main() {
          float intensity = pow(0.68 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
          gl_FragColor = vec4(0.0, 0.95, 1.0, 1.0) * intensity * 0.55;
        }
      `,
      blending: THREE.AdditiveBlending,
      side: THREE.BackSide,
      transparent: true
    });
    const atmosMesh = new THREE.Mesh(atmosGeo, atmosMat);
    scene.add(atmosMesh);

    // 4. Nepal & Terai Coordinates Marker on Globe
    // Nepal Terai: Lat ~26.6° N, Lon ~87.1° E (Koshi Basin)
    const latRad = (26.6 * Math.PI) / 180;
    const lonRad = ((87.1 - 90) * Math.PI) / 180; // offset for 3D alignment

    const markerPos = new THREE.Vector3(
      -(globeRadius * 1.02) * Math.cos(latRad) * Math.cos(lonRad),
      (globeRadius * 1.02) * Math.sin(latRad),
      (globeRadius * 1.02) * Math.cos(latRad) * Math.sin(lonRad)
    );

    // Glowing target ring
    const ringGeo = new THREE.RingGeometry(0.2, 0.35, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.9
    });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.copy(markerPos);
    ringMesh.lookAt(markerPos.clone().multiplyScalar(2));
    globeGroup.add(ringMesh);

    // Beacon pulse cylinder
    const beaconGeo = new THREE.CylinderGeometry(0.05, 0.25, 2.0, 16);
    beaconGeo.translate(0, 1.0, 0);
    const beaconMat = new THREE.MeshBasicMaterial({
      color: 0x00f3ff,
      transparent: true,
      opacity: 0.75
    });
    const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
    beaconMesh.position.copy(markerPos);
    beaconMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), markerPos.clone().normalize());
    globeGroup.add(beaconMesh);

    // 5. Lighting
    const dirLight = new THREE.DirectionalLight(0x38bdf8, 2.2);
    dirLight.position.set(15, 12, 20);
    scene.add(dirLight);

    const ambientLight = new THREE.AmbientLight(0x071126, 1.2);
    scene.add(ambientLight);

    // 6. Camera Animation Sequence
    let startTime = performance.now();
    let hasSkipped = false;

    // Automatic progression fallback timer (8s) in case rAF is throttled by browser
    const autoProgressTimer = setTimeout(() => {
      handleFinishRef.current();
    }, 8000);

    const animate = () => {
      if (hasSkipped) return;
      animFrameId.current = requestAnimationFrame(animate);

      const elapsed = (performance.now() - startTime) / 1000;

      // Rotate globe slowly
      globeGroup.rotation.y = 1.1 + elapsed * 0.12;
      starField.rotation.y = elapsed * 0.01;

      // Pulse ring & beacon
      const pulseScale = 1.0 + Math.sin(elapsed * 4) * 0.25;
      ringMesh.scale.set(pulseScale, pulseScale, 1);
      beaconMat.opacity = 0.5 + Math.sin(elapsed * 5) * 0.4;

      // Stage 1: Planetary approach (0 - 3s)
      if (elapsed < 3.0) {
        const t = elapsed / 3.0;
        camera.position.z = 28 - t * 8; // move from 28 to 20
        camera.position.y = 5 - t * 2;
        setTargetName('SOUTH ASIAN MONSOON DOMAIN');
        setCoordinatesText('28.0000° N, 84.0000° E');
      }
      // Stage 2: Zoom toward Nepal Terai (3 - 6s)
      else if (elapsed < 6.0) {
        const t = (elapsed - 3.0) / 3.0;
        camera.position.z = 20 - t * 7; // move from 20 to 13
        camera.position.y = 3 - t * 1.5;
        camera.position.x = t * 1.8;
        setPhase('zoomed');
        setTargetName('NEPAL TERAI — SAPTAKOSHI BASIN');
        setCoordinatesText('26.6000° N, 87.0500° E (ELEV: 72m)');
      }
      // Stage 3: Lock-on & Ready (6s - 8s)
      else if (elapsed < 8.0) {
        setPhase('ready');
        setTargetName('TARGET LOCKED: EASTERN TERAI FLOODPLAIN');
      }
      // Auto-transition into Mission Control after lock-on
      else {
        handleFinishRef.current();
        return;
      }

      renderer.render(scene, camera);
    };

    animFrameId.current = requestAnimationFrame(animate);

    // Resize handler
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      hasSkipped = true;
      clearTimeout(autoProgressTimer);
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      globeGeo.dispose();
      globeMat.dispose();
      gridGeo.dispose();
      gridMat.dispose();
      starGeometry.dispose();
      starMaterial.dispose();
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className={`fixed inset-0 z-50 bg-command-950 flex flex-col justify-between overflow-hidden transition-opacity duration-300 ${
      isExiting ? 'opacity-0 pointer-events-none' : 'opacity-100'
    }`}>
      {/* 3D WebGL Canvas */}
      <div ref={mountRef} className="absolute inset-0 z-0" />

      {/* Top HUD Bar */}
      <div className="relative z-10 flex items-center justify-between p-6 pointer-events-none">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded border border-cyan-glow/40 bg-command-900/80 backdrop-blur flex items-center justify-center text-cyan-glow shadow-glow-cyan">
            <Compass className="w-5 h-5 animate-spin" style={{ animationDuration: '12s' }} />
          </div>
          <div>
            <div className="text-[10px] uppercase font-mono tracking-widest text-cyan-glow">
              Copernicus Earth Observation Mission
            </div>
            <div className="text-sm font-semibold tracking-wide text-white">
              Sentinel-2 L2A Orbital Ingestion
            </div>
          </div>
        </div>

        {/* Skip Button */}
        <button
          onClick={handleFinish}
          className="pointer-events-auto group px-4 py-2 rounded border border-slate-700 bg-command-900/80 hover:bg-command-800 hover:border-cyan-glow/50 text-xs font-mono text-slate-300 hover:text-cyan-glow transition-all backdrop-blur flex items-center space-x-2 shadow-lg cursor-pointer"
        >
          <span>SKIP CINEMATIC INTRO</span>
          <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>

      {/* Center Target Crosshairs & Telemetry */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center pointer-events-none px-4">
        {/* Optical Sight Ring */}
        <div className="w-72 h-72 rounded-full border border-cyan-glow/20 relative flex items-center justify-center animate-pulse">
          <div className="absolute inset-4 rounded-full border border-dashed border-cyan-glow/30" />
          <div className="w-2 h-2 rounded-full bg-cyan-glow shadow-glow-cyan" />
          <div className="absolute top-0 w-4 h-[1px] bg-cyan-glow" />
          <div className="absolute bottom-0 w-4 h-[1px] bg-cyan-glow" />
          <div className="absolute left-0 h-4 w-[1px] bg-cyan-glow" />
          <div className="absolute right-0 h-4 w-[1px] bg-cyan-glow" />
        </div>

        <div className="mt-6 text-center space-y-1">
          <div className="text-xs font-mono tracking-widest text-cyan-glow flex items-center justify-center space-x-2">
            <span className="inline-block w-2 h-2 rounded-full bg-cyan-glow animate-ping" />
            <span>{targetName}</span>
          </div>
          <div className="text-xs font-mono text-slate-400">
            {coordinatesText}
          </div>
        </div>
      </div>

      {/* Bottom Command Card */}
      <div className="relative z-10 p-8 max-w-2xl mx-auto w-full text-center space-y-4">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full border border-cyan-glow/30 bg-cyan-950/40 text-[11px] font-mono text-cyan-glow backdrop-blur">
          <Sparkles className="w-3.5 h-3.5" />
          <span>NEPAL TERAI RAPID FLOOD INTELLIGENCE &bull; PS-01</span>
        </div>

        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-white drop-shadow-md">
          Disaster Response &amp; Settlement Impact Command Center
        </h1>

        <p className="text-sm text-slate-300 max-w-lg mx-auto font-sans leading-relaxed">
          High-precision multi-spectral change detection using Sentinel-2 Level-2A imagery,
          calibrated MNDWI/NDWI optical indices, and real Terai administrative exposure modeling.
        </p>

        <div className="pt-2 flex items-center justify-center space-x-4 pointer-events-auto">
          <button
            onClick={handleFinish}
            className={`px-6 py-3 rounded bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-semibold text-sm tracking-wide transition-all shadow-glow-cyan flex items-center space-x-2 group cursor-pointer ${
              phase === 'ready' ? 'ring-2 ring-cyan-300 ring-offset-2 ring-offset-command-950 scale-105' : ''
            }`}
          >
            <Navigation className="w-4 h-4 fill-black" />
            <span>ENTER MISSION CONTROL</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        <div className="text-[11px] font-mono text-slate-500">
          EPSG:32644 / 32645 Metric Geodesy &bull; Real Sentinel-2 L2A STAC &bull; Peer-Reviewed Water Indices
        </div>
      </div>
    </div>
  );
};
