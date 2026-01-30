interface VisitStatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
}

export function VisitStatusBadge({ status, size = 'md' }: VisitStatusBadgeProps) {
  const statusConfig: Record<string, { color: string; label: string; icon: string }> = {
    REGISTERED: {
      color: 'bg-blue-100 text-blue-800 border-blue-200',
      label: 'Registered',
      icon: '📝',
    },
    TRIAGED: {
      color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      label: 'Triaged',
      icon: '🩺',
    },
    IN_CONSULTATION: {
      color: 'bg-purple-100 text-purple-800 border-purple-200',
      label: 'In Consultation',
      icon: '👨‍⚕️',
    },
    LAB_REQUESTED: {
      color: 'bg-indigo-100 text-indigo-800 border-indigo-200',
      label: 'Lab Requested',
      icon: '🧪',
    },
    LAB_COMPLETED: {
      color: 'bg-green-100 text-green-800 border-green-200',
      label: 'Lab Completed',
      icon: '✅',
    },
    PHARMACY_PENDING: {
      color: 'bg-orange-100 text-orange-800 border-orange-200',
      label: 'Pharmacy Pending',
      icon: '💊',
    },
    COMPLETED: {
      color: 'bg-gray-100 text-gray-800 border-gray-200',
      label: 'Completed',
      icon: '🏁',
    },
    CANCELLED: {
      color: 'bg-red-100 text-red-800 border-red-200',
      label: 'Cancelled',
      icon: '❌',
    },
  };

  const config = statusConfig[status] || {
    color: 'bg-gray-100 text-gray-800 border-gray-200',
    label: status,
    icon: '❓',
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-1.5 text-base',
  };

  return (
    <span
      className={`
        inline-flex items-center ${sizeClasses[size]} rounded-full border font-medium
        ${config.color}
      `}
    >
      <span className="mr-1.5">{config.icon}</span>
      {config.label}
    </span>
  );
}
