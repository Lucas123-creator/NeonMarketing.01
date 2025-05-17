import React from 'react';

type CardProps = {
  title?: string;
  children: React.ReactNode;
  className?: string;
};

const Card: React.FC<CardProps> = ({ title, children, className = '' }) => (
  <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-4 ${className}`}>
    {title && <h2 className="text-lg font-semibold mb-2">{title}</h2>}
    {children}
  </div>
);

export default Card; 