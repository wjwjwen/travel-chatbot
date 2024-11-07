import React from "react";
import { IconName } from "boxicons";
// https://boxicons.com

interface IconProps {
    name: IconName;
    size?: string;
    color?: string;
    className?: string;
}

const Icon: React.FC<IconProps> = ({ name, className = "", size = "24", color = "" }) => {
    return <i className={`bx bx-${name} ${className}`} style={{ fontSize: `${size}px`, color }} />;
};

export default Icon;
