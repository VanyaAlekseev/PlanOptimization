import { AppBar, Box, Button, Toolbar, Typography } from "@mui/material";
import { PropsWithChildren } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";

const navItems = [
  { label: "Дашборд", to: "/" },
  { label: "Структура изделия", to: "/structure" },
  { label: "Планировщик", to: "/planning" },
  { label: "Алгоритмы", to: "/algorithms" },
  { label: "Отчёты", to: "/reports" }
];

export const Layout = ({ children }: PropsWithChildren) => {
  const location = useLocation();

  return (
    <Box>
      <AppBar position="static" color="primary">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Планирование производства
          </Typography>
          {navItems.map((item) => (
            <Button
              key={item.to}
              color={location.pathname === item.to ? "secondary" : "inherit"}
              component={RouterLink}
              to={item.to}
            >
              {item.label}
            </Button>
          ))}
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ p: 3 }}>{children}</Box>
    </Box>
  );
};

