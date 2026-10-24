import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export const AtmosphericBackground: React.FC = () => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const width = mountRef.current.clientWidth || window.innerWidth;
    const height = mountRef.current.clientHeight || window.innerHeight;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
    } catch (e) {
      console.warn('WebGL not supported for atmospheric background effect, graceful fallback enabled:', e);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 0, 15);

    renderer.setSize(width, height);
    renderer.setPixelRatio(1); // Keep 1x for ultra-smooth background performance
    mountRef.current.appendChild(renderer.domElement);

    // 1. Slow-moving atmospheric particles (representing monsoon moisture & atmospheric depth)
    const particleCount = 280;
    const particleGeo = new THREE.BufferGeometry();
    const particlePos = new Float32Array(particleCount * 3);
    const particleVelocities: { x: number; y: number; z: number }[] = [];

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePos[i] = (Math.random() - 0.5) * 35;
      particlePos[i + 1] = (Math.random() - 0.5) * 25;
      particlePos[i + 2] = (Math.random() - 0.5) * 15;

      particleVelocities.push({
        x: (Math.random() - 0.5) * 0.004,
        y: (Math.random() - 0.5) * 0.003,
        z: (Math.random() - 0.5) * 0.002
      });
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePos, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x00f3ff,
      size: 0.35,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    scene.add(particles);

    // 2. Faint topographic undulating contour plane (Terai lowlands & Himalayan foothills)
    const planeGeo = new THREE.PlaneGeometry(45, 30, 48, 36);
    const posAttr = planeGeo.attributes.position;
    const initialZ = new Float32Array(posAttr.count);

    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i);
      const y = posAttr.getY(i);
      // Create subtle topography
      const z = Math.sin(x * 0.25) * Math.cos(y * 0.25) * 1.2;
      posAttr.setZ(i, z);
      initialZ[i] = z;
    }
    planeGeo.computeVertexNormals();

    const planeMat = new THREE.MeshBasicMaterial({
      color: 0x0077aa,
      wireframe: true,
      transparent: true,
      opacity: 0.045
    });
    const contourPlane = new THREE.Mesh(planeGeo, planeMat);
    contourPlane.position.set(0, -3, -5);
    contourPlane.rotation.x = -Math.PI / 3.2;
    scene.add(contourPlane);

    // 3. Animation loop
    let animId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Ripple contour plane softly
      for (let i = 0; i < posAttr.count; i++) {
        const x = posAttr.getX(i);
        const y = posAttr.getY(i);
        const z = initialZ[i] + Math.sin(x * 0.3 + elapsed * 0.6) * Math.cos(y * 0.3 + elapsed * 0.4) * 0.4;
        posAttr.setZ(i, z);
      }
      posAttr.needsUpdate = true;

      // Drift particles
      const positions = particleGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        const idx = i * 3;
        positions[idx] += particleVelocities[i].x;
        positions[idx + 1] += particleVelocities[i].y;

        // Wrap around bounds
        if (positions[idx] > 18) positions[idx] = -18;
        if (positions[idx] < -18) positions[idx] = 18;
        if (positions[idx + 1] > 12) positions[idx + 1] = -12;
        if (positions[idx + 1] < -12) positions[idx + 1] = 12;
      }
      particleGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

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
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      planeGeo.dispose();
      planeMat.dispose();
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div 
      ref={mountRef} 
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden opacity-80" 
      aria-hidden="true" 
    />
  );
};
