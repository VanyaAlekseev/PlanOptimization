import { configureStore } from "@reduxjs/toolkit";
import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux";

import dashboardReducer from "./store/dashboardSlice";
import structureReducer from "./store/structureSlice";
import planningReducer from "./store/planningSlice";

export const store = configureStore({
  reducer: {
    dashboard: dashboardReducer,
    structure: structureReducer,
    planning: planningReducer
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

