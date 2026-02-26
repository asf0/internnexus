import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";

interface IconContainerProps {
  readonly icon: LucideIcon;
  readonly color: "blue" | "purple" | "green" | "red";
  readonly className?: string;
}

export function IconContainer({ icon: Icon, color, className = "" }: IconContainerProps) {
  const colors = {
    blue: "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400",
    purple: "bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400",
    green: "bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400",
    red: "bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400",
  };

  return (
    <div className={`p-2 rounded-lg ${colors[color]} ${className}`}>
      <Icon className="h-6 w-6" />
    </div>
  );
}
