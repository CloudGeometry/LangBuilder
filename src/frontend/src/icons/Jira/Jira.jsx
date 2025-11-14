const SvgJira = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width="1em"
    height="1em"
    {...props}
  >
    <defs>
      <linearGradient
        id="jira_svg__gradient-1"
        x1="31.825312"
        y1="18.166172"
        x2="19"
        y2="30.988281"
        gradientUnits="userSpaceOnUse"
        gradientTransform="scale(0.21)"
      >
        <stop
          offset="0"
          style={{
            stopColor: "#0052cc",
            stopOpacity: 1,
          }}
        />
        <stop
          offset="1"
          style={{
            stopColor: "#2684ff",
            stopOpacity: 1,
          }}
        />
      </linearGradient>
      <linearGradient
        id="jira_svg__gradient-2"
        x1="41.590939"
        y1="57.471561"
        x2="54.390625"
        y2="44.671875"
        gradientUnits="userSpaceOnUse"
        gradientTransform="scale(0.21)"
      >
        <stop
          offset="0"
          style={{
            stopColor: "#0052cc",
            stopOpacity: 1,
          }}
        />
        <stop
          offset="1"
          style={{
            stopColor: "#2684ff",
            stopOpacity: 1,
          }}
        />
      </linearGradient>
    </defs>
    <path
      d="M 23.7 11.7 L 13.1 1.03 L 12 0 L 0.29 11.7 c -0.38 0.38 -0.38 1.01 0 1.39 l 7.34 7.34 l 4.37 4.37 l 11.71 -11.71 c 0.38 -0.38 0.38 -1.01 0 -1.39 z M 12 16.1 L 8.33 12.4 L 12 8.73 L 15.68 12.4 L 12 16.1 Z"
      fill="#2684ff"
    />
    <path
      d="M 12 8.73 C 9.6 6.33 9.58 2.45 11.98 0.03 L 3.95 8.05 L 8.33 12.4 L 12 8.73 Z"
      fill="url(#jira_svg__gradient-1)"
    />
    <path
      d="M 15.7 12.4 L 12 16.1 c 1.16 1.16 1.81 2.73 1.81 4.37 c 0 1.64 -0.65 3.21 -1.81 4.37 l 8.05 -8.05 L 15.7 12.4 Z"
      fill="url(#jira_svg__gradient-2)"
    />
  </svg>
);
export default SvgJira;
