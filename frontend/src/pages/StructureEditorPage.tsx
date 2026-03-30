import { Box, Button, Grid, Paper, TextField, Typography } from "@mui/material";
import { Tree, TreeApi } from "react-arborist";
import { useRef, useState } from "react";
import { useSnackbar } from "notistack";

import { useAppDispatch, useAppSelector } from "../store";
import { ComponentNode, setSelectedNodeId, setTree } from "../store/structureSlice";
import { api } from "../api/client";
import type { ComponentTreeDto } from "../api/types";

export const StructureEditorPage = () => {
  const dispatch = useAppDispatch();
  const { enqueueSnackbar } = useSnackbar();
  const tree = useAppSelector((s) => s.structure.tree);
  const selectedNodeId = useAppSelector((s) => s.structure.selectedNodeId);
  const treeRef = useRef<TreeApi<ComponentNode>>(null);
  const [productId, setProductId] = useState<number | "">("");

  const loadTree = async (pid: number) => {
    const { data } = await api.get<ComponentTreeDto>("/components/tree", {
      params: { product_id: pid }
    });
    const mapNode = (n: any): ComponentNode => ({
      id: String(n.id),
      name: n.name,
      type: n.type,
      quantity: n.quantity ?? 1,
      children: (n.children ?? []).map(mapNode)
    });
    dispatch(setTree(data.roots.map(mapNode)));
  };

  const handleImportXml = async (value: string) => {
    try {
      if (!productId) {
        enqueueSnackbar("Укажите ID изделия", { variant: "warning" });
        return;
      }
      await api.post("/components/import-xml/", {
        product_id: productId,
        xml_content: value,
        overwrite: true
      });
      await loadTree(productId);
      enqueueSnackbar("XML успешно импортирован", { variant: "success" });
    } catch {
      enqueueSnackbar("Ошибка импорта XML", { variant: "error" });
    }
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Typography variant="h4">Редактор структуры изделия</Typography>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, height: 500, overflow: "auto" }}>
          <Typography variant="subtitle1" gutterBottom>
            Структура (drag-and-drop mock)
          </Typography>
          <Tree<ComponentNode>
            ref={treeRef}
            data={tree}
            // react-arborist использует childrenAccessor, чтобы извлекать children из data-узла
            childrenAccessor={(d) => d.children ?? null}
            onSelect={(nodes) => dispatch(setSelectedNodeId(nodes[0]?.id ?? null))}
          >
            {({ node }) => (
              <Box sx={{ p: 0.5 }}>
                {node.data.name} ({node.data.type}) ×{node.data.quantity}
              </Box>
            )}
          </Tree>
        </Paper>
      </Grid>
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Импорт из XML
          </Typography>
          <TextField
            label="ID изделия (product_id)"
            type="number"
            value={productId}
            onChange={(e) => setProductId(e.target.value === "" ? "" : Number(e.target.value))}
            sx={{ mb: 2 }}
          />
          <TextField
            label="XML"
            placeholder="<project>...</project>"
            multiline
            minRows={6}
            fullWidth
            onBlur={(e) => handleImportXml(e.target.value)}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            В дальнейшем поле будет отправлять XML на backend `/api/components/import-xml/`. Сейчас импорт обрабатывается
            локально (mock).
          </Typography>
        </Paper>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle1" gutterBottom>
            Свойства компонента
          </Typography>
          {selectedNodeId ? (
            <Typography>Выбран компонент: {selectedNodeId}</Typography>
          ) : (
            <Typography color="text.secondary">Выберите компонент в дереве.</Typography>
          )}
          <Button sx={{ mt: 2 }} variant="contained" disabled>
            Сохранить изменения (mock)
          </Button>
        </Paper>
      </Grid>
    </Grid>
  );
};

