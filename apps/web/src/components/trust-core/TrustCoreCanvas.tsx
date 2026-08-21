"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

function CoreSphere({ color, scale = 1 }: { color: string; scale?: number }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.y += delta * 0.15;
  });
  return (
    <mesh ref={ref} scale={scale}>
      <icosahedronGeometry args={[1, 1]} />
      <meshStandardMaterial color={color} wireframe transparent opacity={0.6} />
    </mesh>
  );
}

function OrbitNode({ position, color, speed = 1 }: { position: [number, number, number]; color: string; speed?: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const angle = useMemo(() => Math.random() * Math.PI * 2, []);
  const radius = useMemo(() => 2 + Math.random() * 1.5, []);

  useFrame((state) => {
    if (ref.current) {
      const t = state.clock.elapsedTime * speed * 0.3 + angle;
      ref.current.position.x = Math.cos(t) * radius;
      ref.current.position.z = Math.sin(t) * radius;
      ref.current.position.y = Math.sin(t * 0.5) * 0.5;
    }
  });

  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
    </mesh>
  );
}

function PulseRing() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ref.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 0.8) * 0.1;
      ref.current.scale.set(scale, scale, scale);
    }
  });
  return (
    <mesh ref={ref} rotation={[Math.PI / 2, 0, 0]}>
      <ringGeometry args={[1.8, 1.85, 64]} />
      <meshBasicMaterial color="#00d4ff" transparent opacity={0.15} side={THREE.DoubleSide} />
    </mesh>
  );
}

interface Props {
  activeAgents: number;
  pendingApprovals: number;
  blockedActions: number;
}

export default function TrustCoreCanvas({ activeAgents, pendingApprovals, blockedActions }: Props) {
  const nodeCount = Math.max(activeAgents, 3);
  const nodes = useMemo(
    () =>
      Array.from({ length: nodeCount }, (_, i) => ({
        position: [0, 0, 0] as [number, number, number],
        color: i < pendingApprovals ? "#ffb300" : blockedActions > 0 && i === 0 ? "#ff5252" : "#00e676",
        speed: 0.5 + Math.random() * 0.5,
      })),
    [nodeCount, pendingApprovals, blockedActions]
  );

  return (
    <Canvas camera={{ position: [0, 2, 5], fov: 45 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
      <ambientLight intensity={0.2} />
      <pointLight position={[5, 5, 5]} intensity={0.5} color="#00d4ff" />
      <CoreSphere color="#00d4ff" scale={0.8} />
      <PulseRing />
      {nodes.map((node, i) => (
        <OrbitNode key={i} position={node.position} color={node.color} speed={node.speed} />
      ))}
      <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.3} />
    </Canvas>
  );
}
