// Shared, runtime-free types (safe to import from client components).
export type StatusGroup = "Processing" | "Completed" | "Failed/Cancelled" | "Other";

export type OrderRow = {
  order: string;        // "#123"
  date: string;         // ISO
  status: string;
  statusGrp: StatusGroup;
  type: "Sample Kit" | "Website Order";
  isTest: boolean;
  customer: string;
  email: string;
  phone: string;
  city: string;
  state: string;
  stateCode: string;
  products: string;
  total: number;
  payment: string;
  wcId: number;
};
