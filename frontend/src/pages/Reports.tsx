import { FileText } from "lucide-react";
import { EmptyState } from "@/components/ui/States";
import { Card, CardContent } from "@/components/ui/Card";

export default function Reports() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <Card>
        <CardContent>
          <EmptyState
            icon={<FileText className="h-6 w-6" />}
            title="Report generation is coming next"
            description="Executive summaries, data quality write-ups, and exportable PDF/HTML reports built from your real analysis sessions are planned for a follow-up phase."
          />
        </CardContent>
      </Card>
    </div>
  );
}
