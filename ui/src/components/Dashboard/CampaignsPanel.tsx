import React from 'react';
import Card from '../Shared/Card';
import Loader from '../Shared/Loader';
import Error from '../Shared/Error';
import { useApi } from '../../hooks/useApi';

const CampaignsPanel: React.FC = () => {
  const { data, loading, error, refetch } = useApi<any[]>('/campaigns', 10000);

  const handleAction = (id: string, action: 'launch' | 'pause') => {
    // TODO: Implement launch/pause API call
    alert(`${action} campaign ${id}`);
    refetch();
  };

  return (
    <Card title="Campaigns">
      {loading && <Loader />}
      {error && <Error message={error} />}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              <th className="text-left">Name</th>
              <th>Status</th>
              <th>Templates</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.id} className="border-b">
                <td>{c.name}</td>
                <td>{c.status}</td>
                <td>{c.templates?.join(', ')}</td>
                <td>
                  <button className="mr-2 text-blue-600" onClick={() => handleAction(c.id, 'launch')}>Launch</button>
                  <button className="text-yellow-600" onClick={() => handleAction(c.id, 'pause')}>Pause</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

export default CampaignsPanel; 