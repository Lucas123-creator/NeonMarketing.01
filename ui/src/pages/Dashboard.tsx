import React from 'react';
import OverviewPanel from '../components/Dashboard/OverviewPanel';
import CampaignsPanel from '../components/Dashboard/CampaignsPanel';
import PartnersPanel from '../components/Dashboard/PartnersPanel';
import UGCFeedPanel from '../components/Dashboard/UGCFeedPanel';
import InfluencersPanel from '../components/Dashboard/InfluencersPanel';

const Dashboard: React.FC = () => (
  <div className="max-w-7xl mx-auto p-4 space-y-6">
    <OverviewPanel />
    <div className="grid md:grid-cols-2 gap-6">
      <CampaignsPanel />
      <PartnersPanel />
    </div>
    <div className="grid md:grid-cols-2 gap-6">
      <UGCFeedPanel />
      <InfluencersPanel />
    </div>
  </div>
);

export default Dashboard; 