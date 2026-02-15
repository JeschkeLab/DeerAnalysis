var dagcomponentfuncs = window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

dagcomponentfuncs.DMC_Button = function (props) {
    const {setData, data} = props;

    function onClick() {
        setData();
    }
    let leftIcon, rightIcon;
    if (props.leftIcon) {
        leftIcon = React.createElement(window.dash_iconify.DashIconify, {
            icon: props.leftIcon,
        });
    }
    if (props.rightIcon) {
        rightIcon = React.createElement(window.dash_iconify.DashIconify, {
            icon: props.rightIcon,
        });
    }
    return React.createElement(
        window.dash_mantine_components.Button,
        {
            onClick,
            variant: props.variant,
            color: props.color,
            leftSection: leftIcon,
            rightSection: rightIcon,
            radius: props.radius,
            style: {
                margin: props.margin,
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
            },
        },
        props.value
    );
};

dagcomponentfuncs.DMC_DualIconButton = function (props) {
    const {setData, data} = props;

    function onClickLeft() {
        setData({ action: "left" });
    }

    function onClickRight() {
        setData({ action: "right" });
    }

    const leftButton = React.createElement(
        window.dash_mantine_components.ActionIcon,
        {
            onClick: onClickLeft,
            variant: props.leftVariant || props.variant || "subtle",
            color: props.leftColor || props.color || "blue",
            size: props.size || "sm",
            radius: props.radius || "sm",
        },
        React.createElement(window.dash_iconify.DashIconify, {
            icon: props.leftIcon || "ph:eye",
            width: props.iconSize || 18,
        })
    );

    const rightButton = React.createElement(
        window.dash_mantine_components.ActionIcon,
        {
            onClick: onClickRight,
            variant: props.rightVariant || props.variant || "subtle",
            color: props.rightColor || props.color || "blue",
            size: props.size || "sm",
            radius: props.radius || "sm",
        },
        React.createElement(window.dash_iconify.DashIconify, {
            icon: props.rightIcon || "ph:download-simple",
            width: props.iconSize || 18,
        })
    );

    return React.createElement(
        "div",
        {
            style: {
                display: "flex",
                gap: "4px",
                alignItems: "center",
                height: "100%",
            },
        },
        leftButton,
        rightButton
    );
};