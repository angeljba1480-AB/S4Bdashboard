import { NextResponse } from "next/server";

export const runtime = "edge";

/**
 * Diagnóstico de configuración (temporal). NO expone valores: solo indica si las
 * variables llegaron a producción y el tamaño del dataset. Útil para verificar que
 * REPORT_PASSWORD / REPORT_DATA quedaron bien configuradas tras el deploy.
 */
export async function GET() {
  const pwd = (process.env.REPORT_PASSWORD || "").trim();
  const data = process.env.REPORT_DATA || "";
  return NextResponse.json({
    report_password_set: pwd.length > 0,
    report_password_len: pwd.length, // longitud, no el valor
    report_secret_set: (process.env.REPORT_SECRET || "").length > 0,
    report_data_set: data.trim().length > 0,
    report_data_bytes: data.length,
  });
}
