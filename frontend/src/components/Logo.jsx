// Знак Evergreen — изумрудный лист в круге. Цвет берётся из родителя через currentColor.
export default function Logo({ size = 30, className = "" }) {
  return (
    <span
      className={"grid place-items-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-[0_4px_14px_-4px_rgba(21,160,107,.7)] " + className}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 24 24" width={size * 0.62} height={size * 0.62} fill="none">
        <path
          d="M12 3.2c-4.3 3.4-6.2 6.7-6.2 9.4a6.2 6.2 0 0 0 12.4 0c0-2.7-1.9-6-6.2-9.4Z"
          fill="currentColor"
        />
        <path
          d="M12 7.6v9.8M12 11.6l-2.4-1.6M12 13.8l2.4-1.6"
          stroke="#0a2a1e"
          strokeWidth="1.3"
          strokeLinecap="round"
          opacity=".55"
        />
      </svg>
    </span>
  );
}
