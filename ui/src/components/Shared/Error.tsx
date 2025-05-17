import React from 'react';

type ErrorProps = {
  message: string;
};

const Error: React.FC<ErrorProps> = ({ message }) => (
  <div className="bg-red-100 text-red-700 p-4 rounded mb-4">
    <span className="font-semibold">Error:</span> {message}
  </div>
);

export default Error; 