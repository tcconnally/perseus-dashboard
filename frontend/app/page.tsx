'use client';

import { useState, useEffect } from 'react';
import ServiceCard from '../components/ServiceCard';
import ContextPanel from '../components/ContextPanel';
import MemoryFeed from '../components/MemoryFeed';
import TokenChart from '../components/TokenChart';

const API_URL = ''

interface ServiceStatus {
  name: string;
  status: string;
  latency_ms?: number;
}

export default function DashboardPage() {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [context, setContext] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const projectId = 1; // Demo project

  useEffect(() => {
    async function fetchData() {
      try {
        const [svcRes, ctxRes] = await Promise.all([
          fetch(`${API_URL}/api/projects/${projectId}/services`),
          fetch(`${API_URL}/api/projects/${projectId}/context`),
        ]);
        if (svcRes.ok) setServices(await svcRes.json());
        if (ctxRes.ok) setContext(await ctxRes.json());
      } catch (e) {
        console.log('API not available, using demo data');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  // Demo data when API isn't running
  const demoServices: ServiceStatus[] = [
    { name: 'CI (GitHub Actions)', status: 'up', latency_ms: 234 },
    { name: 'PostgreSQL (Aurora)', status: 'up', latency_ms: 12 },
    { name: 'Redis Cache', status: 'up', latency_ms: 3 },
    { name: 'API Gateway', status: 'up', latency_ms: 45 },
    { name: 'Docker Registry', status: 'up', latency_ms: 89 },
    { name: 'Sentry (Error Tracking)', status: 'up', latency_ms: 156 },
  ];

  const displayServices = services.length > 0 ? services : demoServices;
  const upCount = displayServices.filter(s => s.status === 'up').length;

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">perseus-dashboard</h1>
        <p className="text-gray-400">
          Live context for your AI coding agents &middot; Last resolved: just now
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="card">
          <div className="text-sm text-gray-400 mb-1">Services</div>
          <div className="text-2xl font-bold text-[#3fb950]">{upCount}/{displayServices.length} UP</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-400 mb-1">Context Files</div>
          <div className="text-2xl font-bold">{context?.context_files?.length || 3}</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-400 mb-1">Tokens Saved</div>
          <div className="text-2xl font-bold text-[#5c7cfa]">12,847</div>
        </div>
        <div className="card">
          <div className="text-sm text-gray-400 mb-1">Active Memories</div>
          <div className="text-2xl font-bold text-[#d2991d]">47</div>
        </div>
      </div>

      {/* Services Grid */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Service Health</h2>
        <div className="grid grid-cols-3 gap-3">
          {displayServices.map((svc) => (
            <ServiceCard key={svc.name} name={svc.name} status={svc.status} latency_ms={svc.latency_ms} />
          ))}
        </div>
      </div>

      {/* Two-column: Context + Memory */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <ContextPanel context={context} />
        <MemoryFeed projectId={projectId} />
      </div>

      {/* Analytics Chart */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Token Savings (Last 7 Days)</h2>
        <TokenChart projectId={projectId} />
      </div>
    </div>
  );
}
