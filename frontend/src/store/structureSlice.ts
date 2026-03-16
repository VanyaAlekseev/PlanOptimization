import { createSlice, PayloadAction } from "@reduxjs/toolkit";

export interface ComponentNode {
  id: string;
  name: string;
  type: string;
  quantity: number;
  children?: ComponentNode[];
}

export interface StructureState {
  tree: ComponentNode[];
  selectedNodeId: string | null;
}

const initialState: StructureState = {
  tree: [
    {
      id: "comp_001",
      name: "Плата контроллера",
      type: "assembly",
      quantity: 1,
      children: [
        { id: "comp_002", name: "Микроконтроллер", type: "purchase", quantity: 1 },
        { id: "comp_003", name: "Конденсатор 10мкФ", type: "purchase", quantity: 10 }
      ]
    }
  ],
  selectedNodeId: null
};

const structureSlice = createSlice({
  name: "structure",
  initialState,
  reducers: {
    setSelectedNodeId(state, action: PayloadAction<string | null>) {
      state.selectedNodeId = action.payload;
    },
    setTree(state, action: PayloadAction<ComponentNode[]>) {
      state.tree = action.payload;
    }
  }
});

export const { setSelectedNodeId, setTree } = structureSlice.actions;
export default structureSlice.reducer;

