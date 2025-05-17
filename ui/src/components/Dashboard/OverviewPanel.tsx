import React from 'react';
import Card from '../Shared/Card';
import Loader from '../Shared/Loader';
import Error from '../Shared/Error';
import { useApi } from '../../hooks/useApi';

const OverviewPanel: React.FC = () => {
  const { data: metrics, loading, error } = useApi<any>('/metrics/full', 10000);
  const { data: ugc } = useApi<any>('/growth/ugc');
  const { data: influencers } = useApi<any>('/growth/influencers');
  const { data: referrals } = useApi<any>('/growth/referrals');
  // TODO: Add campaigns/leads endpoints when available

  return (
    <Card title="Overview">
      {loading && <Loader />}
      {error && <Error message={error} />}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="text-2xl font-bold">{ugc?.ugc_feed?.length ?? 0}</div>
          <div className="text-gray-500">UGC Posts</div>
        </div>
        <div>
          <div className="text-2xl font-bold">{influencers?.influencers?.length ?? 0}</div>
          <div className="text-gray-500">Influencers</div>
        </div>
        <div>
          <div className="text-2xl font-bold">{referrals?.referrals?.length ?? 0}</div>
          <div className="text-gray-500">Referrals</div>
        </div>
        <div>
          <div className="text-2xl font-bold">{metrics?.uptime_seconds ? (metrics.uptime_seconds/3600).toFixed(1) : 0}h</div>
          <div className="text-gray-500">System Uptime</div>
        </div>
      </div>
    </Card>
  );
};

export default OverviewPanel; 