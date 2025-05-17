import React from 'react';
import Card from '../Shared/Card';
import Loader from '../Shared/Loader';
import Error from '../Shared/Error';
import { useApi } from '../../hooks/useApi';

const InfluencersPanel: React.FC = () => {
  const { data, loading, error } = useApi<any>('/growth/influencers', 10000);
  const influencers = data?.influencers || [];

  return (
    <Card title="Influencers">
      {loading && <Loader />}
      {error && <Error message={error} />}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              <th>Handle</th>
              <th>Followers</th>
              <th>Engagement</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {influencers.map((inf: any, i: number) => (
              <tr key={i} className="border-b">
                <td>{inf.handle}</td>
                <td>{inf.followers}</td>
                <td>{inf.engagement_rate}</td>
                <td>{inf.status || 'active'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

export default InfluencersPanel; 