import React from 'react';
import Card from '../Shared/Card';
import Loader from '../Shared/Loader';
import Error from '../Shared/Error';
import { useApi } from '../../hooks/useApi';

const PartnersPanel: React.FC = () => {
  const { data, loading, error } = useApi<any>('/growth/referrals', 10000);
  const referrals = data?.referrals || [];

  return (
    <Card title="Partners & Affiliates">
      {loading && <Loader />}
      {error && <Error message={error} />}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr>
              <th>Affiliate Code</th>
              <th>Lead</th>
              <th>Source URL</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {referrals.map((r: any, i: number) => (
              <tr key={i} className="border-b">
                <td>{r.affiliate_code}</td>
                <td>{r.lead_id}</td>
                <td className="truncate max-w-xs">{r.source_url}</td>
                <td>{r.timestamp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
};

export default PartnersPanel; 