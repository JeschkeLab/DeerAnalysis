var dagcomponentfuncs = window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

dagcomponentfuncs.TagsCellRenderer = function (props) {
    const values = props.value || [];
    return React.createElement(
        "div",
        { style: { display: "flex", flexWrap: "wrap", gap: "3px",alignItems: "center", height: "100%" } },
        values.map(function (tag, i) {
            return React.createElement(
                "span",
                {
                    key: i,
                    style: {
                        backgroundColor: "#e0e0e0",
                        borderRadius: "8px",
                        padding: "0px 3px",
                        fontSize: "inherit",
                        lineHeight: "inherit",
                        whiteSpace: "nowrap",
                    },
                },
                tag
            );
        })
    );
};

// Warning counts with icons. props.value is {critical, moderate}, where a
// count of null means the fit was not checked for warnings and shows as "–".
// Levels with no warnings are left out.
dagcomponentfuncs.WarningsCellRenderer = function (props) {
    const value = props.value;
    const unchecked = value === null || value === undefined;
    const levels = [
        { key: "critical", icon: "mdi:alert-circle-outline", color: "red" },
        { key: "moderate", icon: "mdi:alert-outline", color: "orange" },
    ];
    const children = [];
    levels.forEach(function (level) {
        const n = unchecked ? null : value[level.key];
        if (!unchecked && !n) {
            return;
        }
        children.push(
            React.createElement(window.dash_iconify.DashIconify, {
                key: level.key + "-icon", icon: level.icon, width: 16, color: level.color,
            }),
            React.createElement(
                "span",
                { key: level.key + "-count", style: { color: level.color, fontWeight: 700 } },
                unchecked ? "–" : n
            )
        );
    });
    return React.createElement(
        "div",
        { style: { display: "flex", gap: "4px", alignItems: "center", height: "100%" } },
        children
    );
};