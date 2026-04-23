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