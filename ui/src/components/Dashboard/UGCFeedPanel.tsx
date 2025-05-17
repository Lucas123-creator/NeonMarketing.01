import React from 'react';
import Card from '../Shared/Card';
import Loader from '../Shared/Loader';
import Error from '../Shared/Error';
import { useApi } from '../../hooks/useApi';

const UGCFeedPanel: React.FC = () => {
  const { data, loading, error } = useApi<any>('/growth/ugc', 10000);
  const ugc = data?.ugc_feed || [];

  return (
    <Card title="UGC Feed">
      {loading && <Loader />}
      {error && <Error message={error} />}
      <div className="space-y-4">
        {ugc.map((post: any, i: number) => (
          <div key={i} className="p-4 bg-gray-50 dark:bg-gray-900 rounded shadow">
            <div className="font-semibold">{post.author || 'Unknown Author'}</div>
            <div className="text-gray-700 dark:text-gray-300">{post.content}</div>
            <div className="text-xs text-gray-500 mt-1">Platform: {post.platform || 'N/A'} | Score: {post.score ?? 'N/A'}</div>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default UGCFeedPanel; 