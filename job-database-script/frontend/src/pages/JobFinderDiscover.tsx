import React, { useState, useEffect } from 'react';

// Mock types
type SourceStats = {
  total: number;
  enabled: number;
  valid: number;
  by_ats_type: { lever: number; greenhouse: number; ashby: number; workday: number; unknown: number };
  last_discovery_time: string | null;
};

export const JobFinderDiscover: React.FC = () => {
  const [stats, setStats] = useState<SourceStats | null>(null);

  // Note: In a real app, this would fetch from a backend API that reads the JobSource table.
  useEffect(() => {
    // Mock API call
    setStats({
      total: 150,
      enabled: 120,
      valid: 110,
      by_ats_type: {
        lever: 45,
        greenhouse: 50,
        ashby: 10,
        workday: 5,
        unknown: 0
      },
      last_discovery_time: new Date().toISOString()
    });
  }, []);

  const handleSearchSources = (atsType: string) => {
    // 1. Load enabled JobSource records where ats_type matches
    // 2. Fetch jobs from all those sources
    // 3. Filter locally for user's roles/location
    // 4. Save candidates to a JobDiscoveryRun
    // 5. Show first 5 candidates
    // 6. Next 5 pages through the same run
    console.log(`Searching ${atsType} sources... Implementing First 5 / Next 5 logic.`);
  };

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Job Finder - Discover</h1>

      <section className="bg-white shadow p-6 rounded-lg mb-6">
        <h2 className="text-xl font-semibold mb-4">Source Database</h2>
        
        {stats.total === 0 ? (
          <div>
            <p className="text-gray-600 mb-4">
              No saved sources yet. Run <code>scripts/discover_job_sources.py</code> or paste source links to build the database.
            </p>
            <button className="bg-blue-600 text-white px-4 py-2 rounded">
              Seed Example Sources
            </button>
          </div>
        ) : (
          <div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded text-center">
                <p className="text-sm text-gray-500">Total Sources</p>
                <p className="text-2xl font-bold">{stats.total}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded text-center">
                <p className="text-sm text-gray-500">Enabled</p>
                <p className="text-2xl font-bold text-green-600">{stats.enabled}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded text-center">
                <p className="text-sm text-gray-500">Valid</p>
                <p className="text-2xl font-bold text-blue-600">{stats.valid}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded text-center">
                <p className="text-sm text-gray-500">Last Discovery</p>
                <p className="text-sm font-semibold mt-2">
                  {stats.last_discovery_time ? new Date(stats.last_discovery_time).toLocaleDateString() : 'N/A'}
                </p>
              </div>
            </div>

            <h3 className="font-semibold mb-3">Search Available Sources:</h3>
            <div className="flex flex-wrap gap-3">
              <button onClick={() => handleSearchSources('lever')} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded">
                Search Lever Sources ({stats.by_ats_type.lever})
              </button>
              <button onClick={() => handleSearchSources('greenhouse')} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">
                Search Greenhouse Sources ({stats.by_ats_type.greenhouse})
              </button>
              <button onClick={() => handleSearchSources('ashby')} className="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded">
                Search Ashby Sources ({stats.by_ats_type.ashby})
              </button>
              <button onClick={() => handleSearchSources('workday')} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
                Search Workday Sources ({stats.by_ats_type.workday})
              </button>
              <button onClick={() => handleSearchSources('all')} className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded">
                Search All Enabled Sources
              </button>
            </div>
          </div>
        )}
      </section>

    </div>
  );
};
