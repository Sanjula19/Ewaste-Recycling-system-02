import React from 'react';

/** variant: 'success' | 'warning' | 'danger' | 'info' */
export default function Badge({ variant = 'info', children, icon: Icon }) {
  return (
    <span className={`badge badge-${variant}`}>
      {Icon && <Icon size={14} />}
      {children}
    </span>
  );
}
