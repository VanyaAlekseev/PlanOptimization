import { createSlice } from "@reduxjs/toolkit";

export interface PlanningTask {
  id: string;
  name: string;
  start: Date;
  end: Date;
  isCritical: boolean;
}

export interface PlanningState {
  tasks: PlanningTask[];
}

const now = new Date();
const day = 24 * 60 * 60 * 1000;

const initialState: PlanningState = {
  tasks: [
    { id: "t1", name: "Подготовка проекта", start: now, end: new Date(now.getTime() + 3 * day), isCritical: true },
    {
      id: "t2",
      name: "Изготовление прототипа",
      start: new Date(now.getTime() + 3 * day),
      end: new Date(now.getTime() + 10 * day),
      isCritical: true
    }
  ]
};

const planningSlice = createSlice({
  name: "planning",
  initialState,
  reducers: {}
});

export default planningSlice.reducer;

