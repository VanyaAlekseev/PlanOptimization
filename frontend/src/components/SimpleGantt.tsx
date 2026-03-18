import { Box, Typography } from "@mui/material";

export interface SimpleGanttTask {
  id: string;
  name: string;
  start: Date;
  end: Date;
  isCritical: boolean;
}

const DAY_MS = 24 * 60 * 60 * 1000;

export const SimpleGantt = ({ tasks }: { tasks: SimpleGanttTask[] }) => {
  if (!tasks.length) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="text.secondary">Нет задач для отображения.</Typography>
      </Box>
    );
  }

  const minStartMs = Math.min(...tasks.map((t) => t.start.getTime()));
  const maxEndMs = Math.max(...tasks.map((t) => t.end.getTime()));
  const total = Math.max(1, maxEndMs - minStartMs);

  return (
    <Box sx={{ p: 1 }}>
      {tasks
        .slice()
        .sort((a, b) => a.start.getTime() - b.start.getTime())
        .map((t) => {
          const leftPct = ((t.start.getTime() - minStartMs) / total) * 100;
          const widthPct = ((t.end.getTime() - t.start.getTime()) / total) * 100;

          const durationDays = Math.max(0, Math.round((t.end.getTime() - t.start.getTime()) / DAY_MS));
          const bg = t.isCritical ? "#d32f2f" : "#1565c0";

          return (
            <Box key={t.id} sx={{ display: "flex", alignItems: "center", mb: 1, gap: 1 }}>
              <Box sx={{ width: 260, flex: "0 0 auto" }}>
                <Typography variant="body2" noWrap>
                  {t.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t.start.toISOString().slice(0, 10)} - {t.end.toISOString().slice(0, 10)} ({durationDays} дн.)
                </Typography>
              </Box>
              <Box sx={{ position: "relative", height: 18, flex: "1 1 auto", background: "#e9eef3", borderRadius: 1 }}>
                <Box
                  sx={{
                    position: "absolute",
                    left: `${leftPct}%`,
                    width: `${Math.max(2, widthPct)}%`,
                    top: 0,
                    bottom: 0,
                    background: bg,
                    borderRadius: 1
                  }}
                />
              </Box>
            </Box>
          );
        })}
    </Box>
  );
};

